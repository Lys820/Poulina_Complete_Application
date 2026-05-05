using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.Data;
using PouleLabApp.API.DTOs.Request;
using PouleLabApp.API.Models;
using PouleLabApp.API.Services.Interfaces;

namespace PouleLabApp.API.Services
{
    // Implémentation concrète de toutes les opérations métier sur les demandes
    public class AnalysisRequestService : IAnalysisRequestService
    {
        private readonly ApplicationDbContext _context;
        private readonly IAuditLogService _auditLogService;
        public AnalysisRequestService(ApplicationDbContext context,
    IAuditLogService auditLogService)
        {
            _context = context;
            _auditLogService = auditLogService;
        }

        // -------------------------------------------------------
        // Créer une nouvelle demande (brouillon ou soumise)
        // -------------------------------------------------------
        public async Task<RequestDetailDto> CreateAsync(string clientId, CreateRequestDto dto)
        {
            // Vérifier que le laboratoire existe
            var lab = await _context.Laboratories.FindAsync(dto.LaboratoryId)
                ?? throw new KeyNotFoundException("Laboratoire introuvable.");

            // Créer la demande
            var request = new AnalysisRequest
            {
                ClientId = clientId,
                LaboratoryId = dto.LaboratoryId,
                Notes = dto.Notes,
                IsDraft = dto.IsDraft,
                Status = dto.IsDraft ? RequestStatus.Draft : RequestStatus.Submitted,
                CreatedAt = DateTime.UtcNow,
                SubmittedAt = dto.IsDraft ? default : DateTime.UtcNow
            };

            _context.AnalysisRequests.Add(request);
            await _context.SaveChangesAsync();

            // Créer et lier les échantillons à la demande
            foreach (var sampleDto in dto.Samples)
            {
                var sample = new Sample
                {
                    RequestId = request.Id,
                    Type = sampleDto.Type,
                    Characteristics = sampleDto.Characteristics,
                    Quantity = sampleDto.Quantity,
                    Unit = sampleDto.Unit
                };
                _context.Samples.Add(sample);
                await _context.SaveChangesAsync();

                // Créer les résultats vides pour chaque type d'analyse demandé
                // Les valeurs seront remplies plus tard par le laborantin
                foreach (var analysisTypeId in sampleDto.AnalysisTypeIds)
                {
                    var analysisType = await _context.AnalysisTypes.FindAsync(analysisTypeId);
                    if (analysisType == null) continue;

                    _context.AnalysisResults.Add(new AnalysisResult
                    {
                        SampleId = sample.Id,
                        AnalysisTypeId = analysisTypeId,
                        LowerBound = analysisType.ReferenceMin,
                        UpperBound = analysisType.ReferenceMax,
                        RecordedById = clientId // Sera mis à jour par le laborantin
                    });
                }
            }

            await _context.SaveChangesAsync();

            // Retourner la demande créée sous forme de DTO
            return await GetByIdAsync(request.Id)
                ?? throw new Exception("Erreur lors de la récupération de la demande créée.");
        }

        // -------------------------------------------------------
        // Soumettre un brouillon
        // -------------------------------------------------------
        public async Task<RequestDetailDto> SubmitAsync(int requestId, string clientId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Samples)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            // Vérifier que la demande appartient bien au client qui la soumet
            if (request.ClientId != clientId)
                throw new UnauthorizedAccessException("Vous n'êtes pas autorisé à soumettre cette demande.");

            // Vérifier que la demande est bien en brouillon
            if (request.Status != RequestStatus.Draft)
                throw new ArgumentException("Seuls les brouillons peuvent être soumis.");

            // Vérifier qu'au moins un échantillon est présent
            if (!request.Samples.Any())
                throw new ArgumentException("La demande doit contenir au moins un échantillon.");

            // Passer en Submitted
            request.Status = RequestStatus.Submitted;
            request.IsDraft = false;
            request.SubmittedAt = DateTime.UtcNow;

            await _context.SaveChangesAsync();

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Récupérer une demande par son ID avec tous ses détails
        // -------------------------------------------------------
        public async Task<RequestDetailDto?> GetByIdAsync(int requestId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Client)
                .Include(r => r.AssignedTo)
                .Include(r => r.Laboratory)
                .Include(r => r.Samples)
                    .ThenInclude(s => s.Results)
                        .ThenInclude(res => res.AnalysisType)
                .FirstOrDefaultAsync(r => r.Id == requestId);

            if (request == null) return null;

            return MapToDetailDto(request);
        }

        // -------------------------------------------------------
        // Récupérer toutes les demandes avec filtre optionnel
        // -------------------------------------------------------
        public async Task<List<RequestListDto>> GetAllAsync(string? status = null)
        {
            var query = _context.AnalysisRequests
                .Include(r => r.Client)
                .Include(r => r.Laboratory)
                .Include(r => r.Samples)
                .AsQueryable();

            // Appliquer le filtre par statut si fourni
            if (!string.IsNullOrEmpty(status) &&
                Enum.TryParse<RequestStatus>(status, true, out var parsedStatus))
            {
                query = query.Where(r => r.Status == parsedStatus);
            }

            var requests = await query
                .OrderByDescending(r => r.CreatedAt)
                .ToListAsync();

            return requests.Select(MapToListDto).ToList();
        }

        // -------------------------------------------------------
        // Récupérer les demandes d'un client
        // -------------------------------------------------------
        public async Task<List<RequestListDto>> GetByClientAsync(string clientId)
        {
            var requests = await _context.AnalysisRequests
                .Include(r => r.Laboratory)
                .Include(r => r.Samples)
                .Where(r => r.ClientId == clientId)
                .OrderByDescending(r => r.CreatedAt)
                .ToListAsync();

            return requests.Select(MapToListDto).ToList();
        }

        // -------------------------------------------------------
        // Réceptionner une demande (Réceptionniste)
        // -------------------------------------------------------
        public async Task<RequestDetailDto> ReceiveAsync(int requestId)
        {
            var request = await _context.AnalysisRequests.FindAsync(requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.Status != RequestStatus.Submitted)
                throw new ArgumentException("Seules les demandes soumises peuvent être réceptionnées.");

            request.Status = RequestStatus.Received;
            request.ReceivedAt = DateTime.UtcNow;

            await _context.SaveChangesAsync();

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Assigner une demande à un laborantin (Réceptionniste)
        // -------------------------------------------------------
        public async Task<RequestDetailDto> AssignAsync(int requestId, string analystId)
        {
            var request = await _context.AnalysisRequests.FindAsync(requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.Status != RequestStatus.Received)
                throw new ArgumentException("Seules les demandes réceptionnées peuvent être assignées.");

            request.AssignedToId = analystId;
            request.Status = RequestStatus.InProgress;

            await _context.SaveChangesAsync();

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Refuser une demande
        // -------------------------------------------------------
        public async Task<RequestDetailDto> RejectAsync(int requestId, string reason)
        {
            var request = await _context.AnalysisRequests.FindAsync(requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            request.Status = RequestStatus.Closed;
            request.Notes = string.IsNullOrEmpty(request.Notes)
                ? $"Refus : {reason}"
                : $"{request.Notes} | Refus : {reason}";

            await _context.SaveChangesAsync();

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Saisir les résultats d'analyse (Laborantin)
        // IsAnomaly est calculé automatiquement selon les bornes
        // -------------------------------------------------------
        public async Task<RequestDetailDto> SaveResultsAsync(
            int requestId,
            string analystId,
            List<SaveResultDto> results)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Samples)
                    .ThenInclude(s => s.Results)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            // Vérifier que la demande est bien assignée à ce laborantin
            if (request.AssignedToId != analystId)
                throw new UnauthorizedAccessException("Vous n'êtes pas assigné à cette demande.");

            // Vérifier que la demande est en cours d'analyse
            if (request.Status != RequestStatus.InProgress)
                throw new ArgumentException("La demande doit être en cours d'analyse pour saisir des résultats.");

            // Mettre à jour chaque résultat
            foreach (var resultDto in results)
            {
                // Chercher le résultat dans les échantillons de la demande
                var result = request.Samples
                    .SelectMany(s => s.Results)
                    .FirstOrDefault(r => r.Id == resultDto.ResultId)
                    ?? throw new KeyNotFoundException($"Résultat id={resultDto.ResultId} introuvable.");

                // Enregistrer la valeur mesurée
                result.MeasuredValue = resultDto.MeasuredValue;
                result.RecordedById = analystId;
                result.RecordedAt = DateTime.UtcNow;

                // Calcul automatique de l'anomalie
                // IsAnomaly = true si la valeur est en dehors des bornes de référence
                result.IsAnomaly = resultDto.MeasuredValue < result.LowerBound ||
                                resultDto.MeasuredValue > result.UpperBound;
            }

            await _context.SaveChangesAsync();

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Marquer les analyses comme terminées (Laborantin)
        // Passe la demande en InReview pour le chef de labo
        // -------------------------------------------------------
        public async Task<RequestDetailDto> CompleteAnalysisAsync(int requestId, string analystId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Samples)
                    .ThenInclude(s => s.Results)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            // Vérifier que la demande est assignée à ce laborantin
            if (request.AssignedToId != analystId)
                throw new UnauthorizedAccessException("Vous n'êtes pas assigné à cette demande.");

            if (request.Status != RequestStatus.InProgress)
                throw new ArgumentException("La demande doit être en cours d'analyse.");

            // Vérifier que tous les résultats ont été saisis (MeasuredValue != 0)
            var allResults = request.Samples.SelectMany(s => s.Results).ToList();
            if (allResults.Any(r => r.MeasuredValue == 0))
                throw new ArgumentException("Tous les résultats doivent être saisis avant de terminer.");

            // Passer en InReview — le chef de labo peut maintenant valider
            request.Status = RequestStatus.InReview;

            await _context.SaveChangesAsync();

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Valider les résultats (Chef de laboratoire)
        // Passe la demande en Validated — résultats disponibles pour le client
        // -------------------------------------------------------
        public async Task<RequestDetailDto> ValidateAsync(int requestId, string labChiefId)
        {
            var request = await _context.AnalysisRequests
                .FindAsync(requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.Status != RequestStatus.InReview)
                throw new ArgumentException("Seules les demandes en cours de révision peuvent être validées.");

            var oldStatus = request.Status.ToString();

            // Passer en Validated
            request.Status = RequestStatus.Validated;
            await _context.SaveChangesAsync();

            // Enregistrer dans l'historique
            await _auditLogService.LogAsync(
                requestId,
                labChiefId,
                "Validation des résultats",
                oldStatus,
                RequestStatus.Validated.ToString()
            );

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Rejeter et renvoyer à la réception (Chef de laboratoire)
        // Passe la demande en Rejected — sera renvoyée pour re-analyse
        // -------------------------------------------------------
        public async Task<RequestDetailDto> InvalidateAsync(
            int requestId,
            string labChiefId,
            string reason)
        {
            var request = await _context.AnalysisRequests
                .FindAsync(requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.Status != RequestStatus.InReview)
                throw new ArgumentException("Seules les demandes en cours de révision peuvent être rejetées.");

            var oldStatus = request.Status.ToString();

            // Repasser en Received pour relancer le processus depuis la réception
            request.Status = RequestStatus.Rejected;
            request.Notes = string.IsNullOrEmpty(request.Notes)
                ? $"Rejet chef de labo : {reason}"
                : $"{request.Notes} | Rejet chef de labo : {reason}";

            await _context.SaveChangesAsync();

            // Enregistrer dans l'historique
            await _auditLogService.LogAsync(
                requestId,
                labChiefId,
                "Rejet des résultats",
                oldStatus,
                RequestStatus.Rejected.ToString()
            );

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Récupérer l'historique complet d'une demande
        // -------------------------------------------------------
        public async Task<List<AuditLogDto>> GetHistoryAsync(int requestId)
        {
            var logs = await _context.AuditLogs
                .Include(a => a.PerformedBy)
                .Where(a => a.RequestId == requestId)
                .OrderBy(a => a.PerformedAt)
                .ToListAsync();

            return logs.Select(a => new AuditLogDto
            {
                Id = a.Id,
                Action = a.Action,
                PerformedBy = $"{a.PerformedBy?.FirstName} {a.PerformedBy?.LastName}",
                OldValue = a.OldValue,
                NewValue = a.NewValue,
                PerformedAt = a.PerformedAt
            }).ToList();
        }

        // -------------------------------------------------------
        // Méthodes privées de mapping Model → DTO
        // -------------------------------------------------------

        // Convertit une AnalysisRequest en vue allégée pour les listes
        private static RequestListDto MapToListDto(AnalysisRequest r) => new()
        {
            Id = r.Id,
            Status = r.Status.ToString(),
            LaboratoryName = r.Laboratory?.Name ?? "",
            ClientName = $"{r.Client?.FirstName} {r.Client?.LastName}",
            CreatedAt = r.CreatedAt,
            ReceivedAt = r.ReceivedAt,
            IsDraft = r.IsDraft,
            SamplesCount = r.Samples?.Count ?? 0
        };

        // Convertit une AnalysisRequest en vue complète pour le détail
        private static RequestDetailDto MapToDetailDto(AnalysisRequest r) => new()
        {
            Id = r.Id,
            Status = r.Status.ToString(),
            Notes = r.Notes,
            IsDraft = r.IsDraft,
            CreatedAt = r.CreatedAt,
            ReceivedAt = r.ReceivedAt,
            SubmittedAt = r.SubmittedAt,
            LaboratoryName = r.Laboratory?.Name ?? "",
            ClientId = r.ClientId,
            ClientName = $"{r.Client?.FirstName} {r.Client?.LastName}",
            ClientEmail = r.Client?.Email ?? "",
            AssignedToName = r.AssignedTo != null
                ? $"{r.AssignedTo.FirstName} {r.AssignedTo.LastName}"
                : null,
            Samples = r.Samples?.Select(s => new SampleDetailDto
            {
                Id = s.Id,
                Type = s.Type,
                Characteristics = s.Characteristics,
                Quantity = s.Quantity,
                Unit = s.Unit,
                Results = s.Results?.Select(res => new AnalysisResultDetailDto
                {
                    Id = res.Id,
                    AnalysisTypeName = res.AnalysisType?.Name ?? "",
                    MeasuredValue = res.MeasuredValue,
                    LowerBound = res.LowerBound,
                    UpperBound = res.UpperBound,
                    Unit = res.AnalysisType?.Unit ?? "",
                    IsAnomaly = res.IsAnomaly,
                    RecordedAt = res.RecordedAt
                }).ToList() ?? new()
            }).ToList() ?? new()
        };
    }
}