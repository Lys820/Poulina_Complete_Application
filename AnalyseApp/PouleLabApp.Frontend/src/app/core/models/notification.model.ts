export interface NotificationDto {
  id: number;
  message: string;
  isRead: boolean;
  createdAt: Date;
  requestId: number;
  requestStatus: string;
}

export interface UnreadNotificationsResponse {
  count: number;
  notifications: NotificationDto[];
}
