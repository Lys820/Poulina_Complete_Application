export interface UserDto {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phoneNumber?: string;
  filialeName?: string;
  laboratoryId?: number;
  laboratoryName?: string;
  isActive: boolean;
  isApproved: boolean;
  role: string;
  createdAt: string;
}

export interface UpdateUserDto {
  firstName: string;
  lastName: string;
  email: string;
  phoneNumber?: string;
  laboratoryId?: number;
  filialeName: string;
  isActive: boolean;
  role: string;
}

export interface AnalystDto {
  id: string;
  fullName: string;
  email: string;
}
