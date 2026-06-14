namespace PouleLabApp.API.Models
{
    // Type d'analyse réalisable — définit les valeurs de référence pour détecter les anomalies
    public class AnalysisType
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public double ReferenceMin { get; set; }
        public double ReferenceMax { get; set; }
        public string Unit { get; set; } = string.Empty;

        public ICollection<AnalysisResult> Results { get; set; } = new List<AnalysisResult>();
    }
}