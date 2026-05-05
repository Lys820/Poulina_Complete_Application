using PouleLabApp.API.DTOs.Request;

namespace PouleLabApp.API.Services.Interfaces
{
    // Contrat définissant toutes les opérations métier sur les demandes d'analyse
    // Chaque méthode correspond à une action du workflow défini dans le cahier des charges
    public interface IAnalysisRequestService
    {
        // Créer une nouvelle demande (brouillon ou soumise directement)
        Task<RequestDetailDto> CreateAsync(string clientId, CreateRequestDto dto);

        // Soumettre un brouillon existant
        Task<RequestDetailDto> SubmitAsync(int requestId, string clientId);

        // Récupérer une demande par son ID
        Task<RequestDetailDto?> GetByIdAsync(int requestId);

        // Récupérer toutes les demandes (avec filtre optionnel par statut)
        Task<List<RequestListDto>> GetAllAsync(string? status = null);

        // Récupérer toutes les demandes d'un client spécifique
        Task<List<RequestListDto>> GetByClientAsync(string clientId);

        // Réceptionner une demande (Réceptionniste)
        Task<RequestDetailDto> ReceiveAsync(int requestId);

        // Assigner une demande à un laborantin (Réceptionniste)
        Task<RequestDetailDto> AssignAsync(int requestId, string analystId);

        // Refuser une demande (Réceptionniste/Laborantin)
        Task<RequestDetailDto> RejectAsync(int requestId, string reason);
    }
}