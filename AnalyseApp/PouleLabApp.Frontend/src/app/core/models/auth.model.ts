// Miroir des DTOs d'authentification du backend
export interface LoginDto {
  email: string;
  password: string;
}

export interface RegisterDto {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  filialeName: string;
  role: string;
}

export interface AuthResponse {
  token: string;
  refreshToken: string;
  expiresAt: Date;
  userId: string;
  email: string;
  firstName: string;
  lastName: string;
  role: string;
}
