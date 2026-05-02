/** GET /api/profile */
export type ProfileApiV1 = {
  version: "v1"
  id: number
  email: string
  name: string
  resume_text: string | null
  resume_updated_at: string | null
}
