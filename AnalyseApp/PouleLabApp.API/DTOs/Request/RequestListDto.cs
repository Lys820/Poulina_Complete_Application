namespace PouleLabApp.API.DTOs.Request
{
    // Données affichées dans la liste des demandes (vue allégée)
    public class RequestListDto
    {
        public int Id { get; set; }
        public string Status { get; set; } = string.Empty;         // Statut lisible (ex: "InProgress")
        public string LaboratoryName { get; set; } = string.Empty; // Nom du laboratoire
        public string ClientName { get; set; } = string.Empty;     // Nom complet du client
        public DateTime CreatedAt { get; set; }
        public DateTime? ReceivedAt { get; set; }
        public bool IsDraft { get; set; }
        public int SamplesCount { get; set; }                      // Nombre d'échantillons
    }
}