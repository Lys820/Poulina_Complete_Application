export interface UserDto {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phoneNumber?: string;
  filialeName?: string;
  isActive: boolean;
  role: string;
  createdAt: string;
}

export interface UpdateUserDto {
  firstName: string;
  lastName: string;
  filialeName: string;
  isActive: boolean;
  role: string;
}

export interface AnalystDto {
  id: string;
  fullName: string;
  email: string;
}
