namespace PouleLabApp.API.Models
{
    public class AnalysisResult
    {
        public int    Id           { get; set; }
        public int    SampleId     { get; set; }
        public Sample Sample       { get; set; } = null!;

        // Nom libre saisi par le client
        public string AnalysisName { get; set; } = string.Empty;

        // Valeur + bornes saisies par le laborantin
        public double MeasuredValue { get; set; }
        public double LowerBound    { get; set; }
        public double UpperBound    { get; set; }
        public string Unit          { get; set; } = string.Empty;

        public bool     IsAnomaly    { get; set; }
        public string?  RecordedById { get; set; }
        public ApplicationUser? RecordedBy { get; set; }
        public DateTime RecordedAt   { get; set; } = DateTime.UtcNow;
    }
}