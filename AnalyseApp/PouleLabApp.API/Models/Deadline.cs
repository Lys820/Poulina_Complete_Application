namespace PouleLabApp.API.Models
{
    // Échéance associée à une phase d'une demande — permet de détecter les retards
    public class Deadline
    {
        public int Id { get; set; }
        public DeadlinePhase Phase { get; set; }
        public DateTime PlannedDate { get; set; }
        public DateTime? ActualDate { get; set; }
        public bool IsOverdue { get; set; } = false;

        public int RequestId { get; set; }
        public AnalysisRequest Request { get; set; } = null!;

        // Échéance liée à un échantillon spécifique
        public int? SampleId { get; set; }
        public Sample? Sample { get; set; }
    }
}