export interface UserDto {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  filialeName: string;
  isActive: boolean;
  createdAt: Date;
  role: string;
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
