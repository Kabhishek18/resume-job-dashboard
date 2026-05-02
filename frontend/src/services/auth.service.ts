import { apiFetch } from "@/lib/api"
import type { TokenResponse } from "@/types/auth"

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
