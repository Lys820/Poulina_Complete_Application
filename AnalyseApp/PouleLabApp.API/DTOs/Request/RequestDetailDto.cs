namespace PouleLabApp.API.DTOs.Request
{
    // Données complètes d'une demande (vue détaillée)
    public class RequestDetailDto
    {
        public int Id { get; set; }
        public string Status { get; set; } = string.Empty;
        public string Notes { get; set; } = string.Empty;
        public bool IsDraft { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime? ReceivedAt { get; set; }
        public DateTime SubmittedAt { get; set; }
        public int LaboratoryId { get; set; }
        public string LaboratoryName { get; set; } = string.Empty;
        public string ClientId { get; set; } = string.Empty;
        public string ClientName { get; set; } = string.Empty;     // Prénom + Nom
        public string ClientEmail { get; set; } = string.Empty;
        public string? AssignedToId { get; set; }
        public string? AssignedToName { get; set; }                // Laborantin assigné (peut être null)
        public List<SampleDetailDto> Samples { get; set; } = new();
    }

    // Détail d'un échantillon dans la vue complète
    public class SampleDetailDto
    {
        public int Id { get; set; }
        public string Type { get; set; } = string.Empty;
        public string Characteristics { get; set; } = string.Empty;
        public double Quantity { get; set; }
        public string Unit { get; set; } = string.Empty;
        public List<AnalysisResultDetailDto> Results { get; set; } = new();
    }

    // Détail d'un résultat d'analyse dans la vue complète
    public class AnalysisResultDetailDto
    {
        public int    Id            { get; set; }
        public string AnalysisName  { get; set; } = string.Empty;
        public double MeasuredValue { get; set; }
        public double LowerBound    { get; set; }
        public double UpperBound    { get; set; }
        public string Unit          { get; set; } = string.Empty;
        public bool   IsAnomaly     { get; set; }
        public DateTime RecordedAt  { get; set; }
    }
}