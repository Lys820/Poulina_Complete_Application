using Microsoft.AspNetCore.Identity;

namespace PouleLabApp.API.Models
{
    // Utilisateur de l'application — étend IdentityUser pour ajouter les infos métier
    public class ApplicationUser : IdentityUser
    {
        public string FirstName { get; set; } = string.Empty;
        public string LastName { get; set; } = string.Empty;
        public string FilialeName { get; set; } = string.Empty;
        public int? LaboratoryId { get; set; }
        public Laboratory? Laboratory   { get; set; }
        public bool IsActive { get; set; } = true;
        public bool IsApproved { get; set; } = false;
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        public ICollection<AnalysisRequest> SubmittedRequests { get; set; } = new List<AnalysisRequest>();
        public ICollection<AnalysisRequest> AssignedRequests { get; set; } = new List<AnalysisRequest>();
    }
}