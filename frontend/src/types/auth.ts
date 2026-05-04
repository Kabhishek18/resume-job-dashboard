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

export type ForgotPasswordApiV1 = {
  version: "v1"
  message: string
}

export type ResetPasswordApiV1 = {
  version: "v1"
  message: string
}

export type ChangePasswordApiV1 = {
  version: "v1"
  message: string
}
