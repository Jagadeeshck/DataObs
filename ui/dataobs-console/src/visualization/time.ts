export const UTC_TIME_ZONE = "UTC";
export function assertChronological(times: readonly number[]): void {
  for (let i = 1; i < times.length; i++)
    if (times[i] < times[i - 1])
      throw new Error("Time-series points must be chronological");
}
