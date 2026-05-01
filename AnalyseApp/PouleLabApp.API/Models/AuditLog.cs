namespace PouleLabApp.API.Models
{
    // Traçabilité — enregistre chaque action effectuée sur une demande (qui, quoi, quand)
    public class AuditLog
    {
        public int Id { get; set; }
        public string EntityType { get; set; } = string.Empty;
        public string Action { get; set; } = string.Empty;
        public string? OldValue { get; set; }
        public string? NewValue { get; set; }
        public DateTime PerformedAt { get; set; } = DateTime.UtcNow;

        public string PerformedById { get; set; } = string.Empty;
        public ApplicationUser PerformedBy { get; set; } = null!;

        public int RequestId { get; set; }
        public AnalysisRequest Request { get; set; } = null!;
    }
}