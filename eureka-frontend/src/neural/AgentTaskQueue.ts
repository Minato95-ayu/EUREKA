/**
 * AgentTaskQueue
 * 
 * Strict FIFO async lock manager for voice commands.
 * Prevents API race conditions when the user speaks multiple commands
 * back-to-back before the backend inference has completed.
 */
export class AgentTaskQueue {
  private static isProcessing = false
  private static queue: Array<() => Promise<void>> = []

  /**
   * Enqueues an async task and guarantees sequential execution.
   */
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
          // We intentionally catch and swallow the error here 
          // so the queue doesn't completely die for future commands.
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
