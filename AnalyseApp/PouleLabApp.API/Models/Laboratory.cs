namespace PouleLabApp.API.Models
{
    // Laboratoire destinataire d'une demande d'analyse (ex: DICK, SNA, GIPA, MEDOIL)
    public class Laboratory
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string Address { get; set; } = string.Empty;
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        public ICollection<AnalysisRequest> Requests { get; set; } = new List<AnalysisRequest>();
        // Détermine quel template de formulaire PDF utiliser pour ce labo
        public FormTemplateType TemplateType { get; set; } = FormTemplateType.SNA;
    }
}