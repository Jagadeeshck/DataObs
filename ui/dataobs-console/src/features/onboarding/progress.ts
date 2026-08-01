export const onboardingStorageKey = "dataobs.console.onboarding.v1";
export function redactOnboardingProgress(value: {
  step: number;
  goals: string[];
}) {
  return { step: value.step, goals: value.goals };
}
