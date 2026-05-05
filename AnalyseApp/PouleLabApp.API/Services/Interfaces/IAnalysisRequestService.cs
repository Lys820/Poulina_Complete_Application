using PouleLabApp.API.DTOs.Request;

namespace PouleLabApp.API.Services.Interfaces
{
    public interface IAnalysisRequestService
    {
        Task<RequestDetailDto> CreateAsync(string clientId, CreateRequestDto dto);
        Task<RequestDetailDto> SubmitAsync(int requestId, string clientId);
        Task<RequestDetailDto?> GetByIdAsync(int requestId);
        Task<List<RequestListDto>> GetAllAsync(string? status = null);
        Task<List<RequestListDto>> GetByClientAsync(string clientId);
        Task<RequestDetailDto> ReceiveAsync(int requestId);
        Task<RequestDetailDto> AssignAsync(int requestId, string analystId);
        Task<RequestDetailDto> RejectAsync(int requestId, string reason);
        Task<RequestDetailDto> SaveResultsAsync(int requestId, string analystId, List<SaveResultDto> results);
        Task<RequestDetailDto> CompleteAnalysisAsync(int requestId, string analystId);

        // Valider les résultats (Chef de labo)
        Task<RequestDetailDto> ValidateAsync(int requestId, string labChiefId);

        // Rejeter et renvoyer à la réception (Chef de labo)
        Task<RequestDetailDto> InvalidateAsync(int requestId, string labChiefId, string reason);

        // Récupérer l'historique complet d'une demande
        Task<List<AuditLogDto>> GetHistoryAsync(int requestId);
    }
}