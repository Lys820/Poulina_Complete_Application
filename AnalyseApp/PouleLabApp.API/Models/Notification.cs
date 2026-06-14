namespace PouleLabApp.API.Models
{
    // Notification interne envoyée à un utilisateur lors d'un changement d'état d'une demande
    public class Notification
    {
        public int Id { get; set; }
        public string Message { get; set; } = string.Empty;
        public bool IsRead { get; set; } = false;
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        public string RecipientId { get; set; } = string.Empty;
        public ApplicationUser Recipient { get; set; } = null!;

        public int? RequestId { get; set; }
        public AnalysisRequest? Request { get; set; } = null!;
    }
}