namespace PouleLabApp.API.Models
{
    // Résultat d'une analyse sur un échantillon — IsAnomaly est calculé automatiquement
    public class AnalysisResult
    {
        public int Id { get; set; }
        public double MeasuredValue { get; set; }
        public double LowerBound { get; set; }
        public double UpperBound { get; set; }
        public bool IsAnomaly { get; set; } // true si MeasuredValue < LowerBound || > UpperBound
        public DateTime RecordedAt { get; set; } = DateTime.UtcNow;

        public int SampleId { get; set; }
        public Sample Sample { get; set; } = null!;

        public int AnalysisTypeId { get; set; }
        public AnalysisType AnalysisType { get; set; } = null!;

        public string RecordedById { get; set; } = string.Empty;
        public ApplicationUser RecordedBy { get; set; } = null!;
    }
}