export type ParsedResume = {
  skills: string[]
  experience_years_est?: number | null
  education: string[]
  tools: string[]
  keywords: string[]
}

export type ParseResumeResponse = {
  parsed: ParsedResume
  cleaned_text_preview: string
}

export type ParseResumeApiV1 = ParseResumeResponse & {
  version: "v1"
}
