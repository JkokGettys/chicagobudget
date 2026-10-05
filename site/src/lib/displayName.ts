/** Presentation only. Never use a display name as an ID or replace source data with it. */
export type NamedBox = { name: string; short_name?: string | null };

// Exact aliases only: unfamiliar programs and spending categories stay intact.
const aliases = new Map<string, string>([
  ['Chicago Police Department', 'Police'], ['Chicago Fire Department', 'Fire'],
  ['Chicago Department of Transportation', 'Transportation'], ['Chicago Department of Aviation', 'Aviation'],
  ['Department of Water Management', 'Water Management'], ['Department of Streets and Sanitation', 'Streets & Sanitation'],
  ['Chicago Department of Public Health', 'Public Health'], ['Chicago Public Library', 'Public Library'],
  ['Department of Family and Support Services', 'Family Services'],
  ['Office of Emergency Management and Communications', 'Emergency Management'],
  ['Civilian Office of Police Accountability', 'Police Accountability'],
  ['Office of Public Safety Administration', 'Public Safety Admin'],
  ['Department of Fleet and Facility Management', 'Fleet & Facilities'],
]);
const programs = [
  ['DOT - FHWA - IDOT - CTY - Highway Planning and Construction (20.205)', 'Highway Planning and Construction (20.205)', 'Highway planning and construction'],
  ['DOT - FTA - Federal Transit Formula Grants (20.507)', 'Federal Transit Formula Grants (20.507)', 'Federal transit grants'],
  ['DOT - NHTSA - IDOT - National Priority Safety Programs (20.616)', 'National Priority Safety Programs (20.616)', 'National priority safety'],
  ['DOT - NHTSA - IDOT - State and Community Highway Safety (20.600)', 'State and Community Highway Safety (20.600)', 'Community highway safety'],
] as const;
for (const [official, program, short] of programs) {
  aliases.set(official, short);
  aliases.set(program, short);
  aliases.set(`Construction of Buildings and Other Structures (${official})`, short);
  // Retain the spending distinction when the same program funds other categories.
  aliases.set(`Reserve Balance (${official})`, `${short} · Reserve balance`);
  aliases.set(`Fringe Benefits (${official})`, `${short} · Fringe benefits`);
  aliases.set(`For Professional and Technical Services and Other Third Party Benefit Agreements (${official})`, `${short} · Professional and technical services`);
}

export function displayName(item: NamedBox): string {
  // Generated ellipsis labels hide the distinguishing program. Prefer the official
  // name for unknown items rather than perpetuating those lossy prefix truncations.
  const short = item.short_name;
  return aliases.get(item.name) ?? (short?.trim() && !/(?:…|\.\.\.)$/.test(short.trim()) ? short : item.name);
}

/** Both the full source title and the visible alias remain searchable. */
export function nameSearchText(item: NamedBox): string {
  return `${item.name} ${item.short_name ?? ''} ${displayName(item)}`.toLocaleLowerCase();
}
