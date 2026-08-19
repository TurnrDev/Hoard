import { getContexts, type CampaignContext } from "./api";

export type ActingContext = CampaignContext;

const storageKey = "hoard:last-context";

export function contextPath(context: ActingContext): string {
  return `/c/${context.id}`;
}

export function rememberContext(context: ActingContext): void {
  localStorage.setItem(storageKey, String(context.id));
}

export async function contexts(): Promise<ActingContext[]> {
  return getContexts();
}

export async function defaultContext(): Promise<ActingContext | undefined> {
  const available = await contexts();
  const remembered = Number(localStorage.getItem(storageKey));
  return available.find((context) => context.id === remembered) ?? available[0];
}
