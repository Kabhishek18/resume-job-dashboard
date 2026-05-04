import { apiFetch } from "@/lib/api"
import type {
  ChangePasswordApiV1,
  ForgotPasswordApiV1,
  ResetPasswordApiV1,
  TokenResponse,
} from "@/types/auth"

export type RegisterBody = {
  name: string
  email: string
  password: string
  confirm_password: string
}

export type LoginBody = {
  email: string
  password: string
}

export type ChangePasswordBody = {
  current_password: string
  new_password: string
  confirm_password: string
}

export type ResetPasswordBody = {
  token: string
  new_password: string
  confirm_password: string
}

export function postRegister(body: RegisterBody): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}

export function postLogin(body: LoginBody): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}

export function postChangePassword(token: string, body: ChangePasswordBody): Promise<ChangePasswordApiV1> {
  return apiFetch<ChangePasswordApiV1>("/api/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    token,
    body: JSON.stringify(body),
  })
}

export function postForgotPassword(email: string): Promise<ForgotPasswordApiV1> {
  return apiFetch<ForgotPasswordApiV1>("/api/auth/forgot-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  })
}

export function postResetPassword(body: ResetPasswordBody): Promise<ResetPasswordApiV1> {
  return apiFetch<ResetPasswordApiV1>("/api/auth/reset-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}
