export function displayModel(
  model: string | null | undefined,
  fallback = "No model",
) {
  return model && !/seed/i.test(model) ? model : fallback;
}