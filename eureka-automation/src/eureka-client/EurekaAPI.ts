import axios, { type AxiosInstance } from "axios";

export class EurekaAPI {
  private client: AxiosInstance;

  constructor(baseURL = process.env.EUREKA_API_URL || "http://localhost:8000") {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: { "Content-Type": "application/json" }
    });
  }

  async createExperiment(name: string, objective: string): Promise<unknown> {
    const response = await this.client.post("/api/experiments", null, {
      params: { name, objective }
    });
    return response.data;
  }

  async createSimulation(data: {
    experiment_id: string;
    name: string;
    description: string;
    simulation_type?: string;
  }): Promise<{ simulation_id: string; status: string }> {
    const response = await this.client.post("/api/simulations/create", data);
    return response.data;
  }

  async runSimulation(simulationId: string, steps = 100, timeStep = 0.001): Promise<unknown> {
    const response = await this.client.post(`/api/simulations/${simulationId}/run`, {
      steps,
      time_step: timeStep
    });
    return response.data;
  }

  async askARIA(message: string, experimentContext: Record<string, unknown> = {}): Promise<unknown> {
    const response = await this.client.post("/api/agents/process", null, {
      params: {
        message: `${message}\n\nAutomation context:\n${JSON.stringify(experimentContext, null, 2)}`
      }
    });
    return response.data;
  }

  async health(): Promise<unknown> {
    const response = await this.client.get("/health");
    return response.data;
  }
}
