namespace PouleLabApp.API.DTOs.Pdf
{
    // Données nécessaires à la génération du bulletin d'analyses PDF
    public class BulletinReportDto
    {
        public int RequestId { get; set; }
        public string LaboratoryName { get; set; } = string.Empty;
        public string ClientName { get; set; } = string.Empty;
        public string ClientEmail { get; set; } = string.Empty;
        public string ClientFiliale { get; set; } = string.Empty;
        public DateTime SubmittedAt { get; set; }
        public DateTime ValidatedAt { get; set; }
        public List<SampleReportDto> Samples { get; set; } = new();
    }

    // Données d'un échantillon dans le bulletin
    public class SampleReportDto
    {
        public string Type { get; set; } = string.Empty;
        public string Characteristics { get; set; } = string.Empty;
        public double Quantity { get; set; }
        public string Unit { get; set; } = string.Empty;
        public List<ResultReportDto> Results { get; set; } = new();
    }

    // Données d'un résultat dans le bulletin
    public class ResultReportDto
    {
        public string AnalysisTypeName { get; set; } = string.Empty;
        public double MeasuredValue { get; set; }
        public double LowerBound { get; set; }
        public double UpperBound { get; set; }
        public string Unit { get; set; } = string.Empty;
        public bool IsAnomaly { get; set; }  // Affiché en rouge dans le bulletin
    }
}