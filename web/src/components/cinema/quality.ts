/**
 * The adaptive quality of the Act I stage. It times the frames it draws; when the average over a window
 * is above the budget, it sheds the optional effects (grain, chromatic edge, mist) and lowers the canvas
 * resolution. It only steps down, once: a stage that cannot hold 50 fps on this device keeps the cheaper look.
 */
export class QualityManager {
  private level = 0;
  private samples = 0;
  private sum = 0;

  constructor(
    private readonly budgetMs = 20,
    private readonly windowSize = 60,
  ) {}

  /** The optional effects are on at full quality. */
  get effects(): boolean {
    return this.level === 0;
  }

  /** Canvas resolution scale. */
  get scale(): number {
    return this.level === 0 ? 1 : 0.75;
  }

  /** Records one drawn frame (ms). Returns true when the level just dropped. */
  sample(ms: number): boolean {
    if (this.level > 0) return false;
    // A tab coming back from the background is one long frame, not a slow stage.
    this.sum += Math.min(ms, 100);
    this.samples += 1;
    if (this.samples < this.windowSize) return false;
    const avg = this.sum / this.samples;
    this.samples = 0;
    this.sum = 0;
    if (avg <= this.budgetMs) return false;
    this.level = 1;
    return true;
  }
}
