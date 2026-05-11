namespace PouleLabApp.API.DTOs.Notification
{
    // Représente une notification envoyée à un utilisateur
    public class NotificationDto
    {
        public int Id { get; set; }
        public string Message { get; set; } = string.Empty;
        public bool IsRead { get; set; }
        public DateTime CreatedAt { get; set; }
        public int RequestId { get; set; }          // Lien vers la demande concernée
        public string RequestStatus { get; set; } = string.Empty;
    }
}