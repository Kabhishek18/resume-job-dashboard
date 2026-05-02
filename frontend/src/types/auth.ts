export type AuthUser = {
  id: number
  email: string
  name: string
}

export type TokenResponse = {
  access_token: string
  token_type: string
  user: AuthUser
}
