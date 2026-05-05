namespace PouleLabApp.API.DTOs.Request
{
    // Données envoyées par le client pour créer une nouvelle demande d'analyse
    public class CreateRequestDto
    {
        public int LaboratoryId { get; set; }           // Laboratoire destinataire
        public string Notes { get; set; } = string.Empty; // Remarques libres du client
        public bool IsDraft { get; set; } = true;       // true = brouillon, false = soumis directement
        public List<CreateSampleDto> Samples { get; set; } = new(); // Échantillons joints à la demande
    }

    // Données d'un échantillon inclus dans la demande
    public class CreateSampleDto
    {
        public string Type { get; set; } = string.Empty;           // Type d'échantillon (ex: Huile, Eau)
        public string Characteristics { get; set; } = string.Empty; // Description physique
        public double Quantity { get; set; }                        // Quantité
        public string Unit { get; set; } = string.Empty;           // Unité (ex: ml, g)
        public List<int> AnalysisTypeIds { get; set; } = new();    // Types d'analyses demandées pour cet échantillon
    }
}