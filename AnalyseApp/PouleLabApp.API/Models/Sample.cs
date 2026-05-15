namespace PouleLabApp.API.Models
{
    // Échantillon physique soumis dans une demande d'analyse
    public class Sample
    {
        public int Id { get; set; }
        public string Type { get; set; } = string.Empty;
        public string Characteristics { get; set; } = string.Empty;
        public double Quantity { get; set; }
        public string Unit { get; set; } = string.Empty;

        public int RequestId { get; set; }
        public AnalysisRequest Request { get; set; } = null!;

        public ICollection<AnalysisResult> Results { get; set; } = new List<AnalysisResult>();
        public ICollection<Deadline> Deadlines { get; set; } = new List<Deadline>();
    }
}