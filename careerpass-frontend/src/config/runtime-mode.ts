export type DataMode = "mock" | "api";

export function getDataMode(): DataMode {
  const configured = import.meta.env.VITE_DATA_MODE;
  if (configured === "mock") return "mock";
  if (configured === "api") return "api";
  return import.meta.env.MODE === "demo" ? "mock" : "api";
}

export function isMockMode(): boolean {
  return getDataMode() === "mock";
}
