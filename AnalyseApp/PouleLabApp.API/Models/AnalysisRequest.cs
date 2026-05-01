namespace PouleLabApp.API.Models
{
    // Entité centrale — représente une demande d'analyse du dépôt jusqu'à la livraison des résultats
    public class AnalysisRequest
    {
        public int Id { get; set; }
        public RequestStatus Status { get; set; } = RequestStatus.Draft;
        public string Notes { get; set; } = string.Empty;
        public bool IsDraft { get; set; } = true;
        public DateTime SubmittedAt { get; set; }
        public DateTime? ReceivedAt { get; set; }
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        public string ClientId { get; set; } = string.Empty;
        public ApplicationUser Client { get; set; } = null!;

        public string? AssignedToId { get; set; }
        public ApplicationUser? AssignedTo { get; set; }

        public int LaboratoryId { get; set; }
        public Laboratory Laboratory { get; set; } = null!;

        public ICollection<Sample> Samples { get; set; } = new List<Sample>();
        public ICollection<Deadline> Deadlines { get; set; } = new List<Deadline>();
        public ICollection<AuditLog> AuditLogs { get; set; } = new List<AuditLog>();
        public ICollection<Notification> Notifications { get; set; } = new List<Notification>();
    }
}