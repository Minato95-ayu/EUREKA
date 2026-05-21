import { Queue, Worker, type Job } from "bullmq";
import IORedis from "ioredis";
import { EurekaAPI } from "../eureka-client/EurekaAPI.js";
import type { ExperimentJob } from "../types.js";
import { logger } from "../utils/logger.js";

export class BatchProcessor {
  private redis: IORedis;
  private queue: Queue<ExperimentJob>;
  private workers: Worker<ExperimentJob>[] = [];
  private eureka = new EurekaAPI();

  constructor(concurrency = Number(process.env.AUTOMATION_CONCURRENCY || 4)) {
    this.redis = new IORedis({
      host: process.env.REDIS_HOST || "localhost",
      port: Number(process.env.REDIS_PORT || 6379),
      maxRetriesPerRequest: null
    });

    this.queue = new Queue<ExperimentJob>("eureka-experiments", {
      connection: this.redis
    });

    for (let i = 0; i < concurrency; i += 1) {
      this.createWorker(i);
    }
  }

  async addBatch(experiments: Array<Omit<ExperimentJob, "experimentId">>): Promise<string[]> {
    const jobs = await this.queue.addBulk(
      experiments.map((experiment) => ({
        name: "experiment",
        data: {
          ...experiment,
          experimentId: `auto_${Date.now()}_${Math.random().toString(36).slice(2)}`
        },
        opts: {
          attempts: 3,
          priority: experiment.priority,
          backoff: { type: "exponential", delay: 2000 }
        }
      }))
    );

    return jobs.map((job) => String(job.id));
  }

  async getStats(): Promise<Record<string, number>> {
    return {
      waiting: await this.queue.getWaitingCount(),
      active: await this.queue.getActiveCount(),
      completed: await this.queue.getCompletedCount(),
      failed: await this.queue.getFailedCount()
    };
  }

  async cleanup(): Promise<void> {
    await this.queue.close();
    await Promise.all(this.workers.map((worker) => worker.close()));
    await this.redis.quit();
  }

  private createWorker(workerId: number): void {
    const worker = new Worker<ExperimentJob>(
      "eureka-experiments",
      async (job: Job<ExperimentJob>) => this.processExperiment(job.data, workerId),
      { connection: this.redis, concurrency: 1 }
    );

    worker.on("completed", (job) => logger.info(`Worker ${workerId} completed job ${job.id}`));
    worker.on("failed", (job, error) => logger.error(`Worker ${workerId} failed job ${job?.id}: ${error.message}`));
    this.workers.push(worker);
  }

  private async processExperiment(job: ExperimentJob, workerId: number): Promise<unknown> {
    logger.info(`Worker ${workerId} processing ${job.name}`);

    const simulation = await this.eureka.createSimulation({
      experiment_id: job.experimentId,
      name: job.name,
      description: `Automation experiment: ${job.type}`,
      simulation_type: job.type
    });

    const result = await this.eureka.runSimulation(simulation.simulation_id, 100, 0.001);
    const analysis = await this.eureka.askARIA(`Analyze automation experiment "${job.name}"`, {
      automationJob: job,
      simulationResult: result
    });

    return {
      experimentId: job.experimentId,
      simulationId: simulation.simulation_id,
      result,
      analysis
    };
  }
}
