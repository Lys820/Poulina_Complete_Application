namespace PouleLabApp.API.DTOs.Request
{
    // Données modifiables d'une demande — uniquement si elle est en brouillon
    public class UpdateRequestDto
    {
        public int LaboratoryId { get; set; }
        public string Brand { get; set; } = string.Empty;
        public string Notes { get; set; } = string.Empty;
        public bool IsDraft { get; set; }
        public List<CreateSampleDto> Samples { get; set; } = new();
    }
}