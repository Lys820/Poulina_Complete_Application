using PouleLabApp.API.Models;

namespace PouleLabApp.API.Services.Interfaces
{
    // Contrat du service de traçabilité
    // Chaque changement de statut d'une demande doit être enregistré
    public interface IAuditLogService
    {
        Task LogAsync(
            int requestId,
            string performedById,
            string action,
            string? oldValue = null,
            string? newValue = null);
    }
}