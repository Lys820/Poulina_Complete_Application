using PouleLabApp.API.DTOs.Request;

namespace PouleLabApp.API.Services.Interfaces
{
    public interface IAnalysisRequestService
    {
        Task<RequestDetailDto> CreateAsync(string clientId, CreateRequestDto dto);
        Task<RequestDetailDto> SubmitAsync(int requestId, string clientId);
        Task<RequestDetailDto?> GetByIdAsync(int requestId);
<<<<<<< HEAD
        Task<List<RequestListDto>> GetAllAsync(
            string? status = null,
            string? userId = null,
            int? laboratoryId = null);
=======
        Task<List<RequestListDto>> GetAllAsync(string? status = null, int? laboratoryId = null);
>>>>>>> origin/Lilia
        Task<List<RequestListDto>> GetByClientAsync(string clientId);
        Task<RequestDetailDto> ReceiveAsync(int requestId, string receptionistId);
        Task<RequestDetailDto> AssignAsync(int requestId, string analystId);
        Task<RequestDetailDto> SaveResultsAsync(int requestId, string analystId, List<SaveResultDto> results);
        Task<RequestDetailDto> CompleteAnalysisAsync(int requestId, string analystId);

        // Valider les résultats (Chef de labo)
        Task<RequestDetailDto> ValidateAsync(int requestId, string labChiefId);

        // Rejeter et renvoyer à la réception (Chef de labo)
        Task<RequestDetailDto> InvalidateAsync(int requestId, string labChiefId, string reason);

        // Récupérer l'historique complet d'une demande
        Task<List<AuditLogDto>> GetHistoryAsync(int requestId);

        // Définir les échéances d'une demande
        Task<RequestDetailDto> SetDeadlinesAsync(int requestId, List<SetDeadlineDto> deadlines);

        // Récupérer les échéances d'une demande
        Task<List<DeadlineDto>> GetDeadlinesAsync(int requestId);

        // Modifier une demande existante — uniquement si en brouillon
        Task<RequestDetailDto> UpdateAsync(int requestId, string userId, UpdateRequestDto dto);
    
        // Laborantin accepte la demande assignée
        Task<RequestDetailDto> AnalystAcceptAsync(int requestId, string analystId);

        // Laborantin refuse la demande assignée — clôture automatique
        Task<RequestDetailDto> AnalystRejectAsync(int requestId, string analystId, string reason);

        //Supression d'une demande — uniquement si en brouillon
        Task DeleteAsync(int requestId);

        //Suppression d'une échéance - uniquement si pas encore réceptionné
        Task DeleteDeadlineAsync(int deadlineId);
    }
}