export type CampaignCalendar = {
  era_abbreviation: string;
  era_name: string;
  year: number;
  day: number;
};

export function ordinal(value: number): string {
  const remainder = value % 100;
  if (remainder >= 11 && remainder <= 13) return `${value}th`;
  return `${value}${{ 1: "st", 2: "nd", 3: "rd" }[value % 10] ?? "th"}`;
}

export function formatCampaignDate(calendar: CampaignCalendar): string {
  return `${calendar.era_abbreviation}${calendar.year}, ${ordinal(calendar.day)}`;
}
