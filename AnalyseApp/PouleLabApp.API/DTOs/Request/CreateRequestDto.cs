namespace PouleLabApp.API.DTOs.Request
{
    // Données envoyées par le client pour créer une nouvelle demande d'analyse
    public class CreateRequestDto
    {
        public int LaboratoryId { get; set; }           // Laboratoire destinataire
        public string Brand { get; set; } = string.Empty; // Marque du produit à analyser
        public string Notes { get; set; } = string.Empty; // Remarques libres du client
        public bool IsDraft { get; set; } = true;       // true = brouillon, false = soumis directement
        public List<CreateSampleDto> Samples { get; set; } = new(); // Échantillons joints à la demande
    }

    // Données d'un échantillon inclus dans la demande
    public class CreateSampleDto
    {
        public string Type            { get; set; } = string.Empty;
        public string Characteristics { get; set; } = string.Empty;
        public double Quantity        { get; set; }
        public string Unit            { get; set; } = string.Empty;

        // Noms libres des analyses — ex: "pH", "Viscosité à 40°C"
        public List<string> AnalysisNames { get; set; } = new();
    }
}