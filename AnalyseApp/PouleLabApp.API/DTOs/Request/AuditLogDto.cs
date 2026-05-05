namespace PouleLabApp.API.DTOs.Request
{
    // Représente une entrée dans l'historique d'une demande
    // Permet de tracer qui a fait quoi et quand sur chaque demande
    public class AuditLogDto
    {
        public int Id { get; set; }
        public string Action { get; set; } = string.Empty;      // Ex: "Soumission", "Validation"
        public string PerformedBy { get; set; } = string.Empty; // Nom de l'auteur de l'action
        public string? OldValue { get; set; }                   // Ancien statut
        public string? NewValue { get; set; }                   // Nouveau statut
        public DateTime PerformedAt { get; set; }               // Date et heure de l'action
    }
}