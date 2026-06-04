namespace PouleLabApp.API.Models
{
    public class Deadline
    {
        public int Id { get; set; }

        public int RequestId { get; set; }
        public AnalysisRequest Request { get; set; } = null!;

        public int SampleId { get; set; }
        public Sample Sample { get; set; } = null!;

        // Péremption
        public bool IsPerishable { get; set; } = false;
        public DateTime? ExpiryDate { get; set; }

        // Urgence
        public string UrgencyLevel       { get; set; } = "Normal";
        public string UrgencyDescription { get; set; } = string.Empty;
    }
}