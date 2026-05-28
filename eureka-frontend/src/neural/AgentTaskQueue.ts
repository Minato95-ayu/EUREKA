// simple queue to prevent voice commands from stepping on each other
export class AgentTaskQueue {
  private static isProcessing = false
  private static queue: Array<() => Promise<void>> = []

  // push to queue and run sequentially
  public static async enqueue(task: () => Promise<void>): Promise<void> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        try {
          await task()
          resolve()
        } catch (e) {
          reject(e)
        }
      })

      this.flush()
    })
  }

  private static async flush() {
    if (this.isProcessing) return
    if (this.queue.length === 0) return

    this.isProcessing = true
    
    while (this.queue.length > 0) {
      const task = this.queue.shift()
      if (task) {
        try {
          await task()
        } catch (error) {
          console.error('[AgentTaskQueue] Task failed:', error)
          // swallow error so queue doesn't die
        }
      }
    }

    this.isProcessing = false
  }

  public static clear() {
    this.queue = []
    this.isProcessing = false
  }
}
