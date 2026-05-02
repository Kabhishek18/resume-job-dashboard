export type JobDescriptionInput = {
  title?: string | null
  company?: string | null
  raw_text: string
  /** Original posting URL — provenance; matcher uses raw_text. */
  url?: string | null
}
