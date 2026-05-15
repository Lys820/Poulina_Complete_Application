namespace PouleLabApp.API.DTOs.Request
{
    // Représente une échéance associée à une phase du workflow
    public class DeadlineDto
    {
        public int Id { get; set; }
        public string Phase { get; set; } = string.Empty;      // Ex: "Reception", "Analysis"
        public DateTime PlannedDate { get; set; }              // Date limite prévue
        public DateTime? ActualDate { get; set; }              // Date réelle de complétion
        public bool IsOverdue { get; set; }                    // true si délai dépassé
        public int? SampleId { get; set; }
        public string SampleType { get; set; } = string.Empty;
    }

    // Données envoyées pour définir une échéance
    public class SetDeadlineDto
    {
        public string Phase { get; set; } = string.Empty;      // Phase concernée
        public DateTime PlannedDate { get; set; }              // Date limite à respecter
        public int? SampleId { get; set; }
    }
}