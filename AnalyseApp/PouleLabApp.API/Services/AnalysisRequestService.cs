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
        private readonly IEmailService _emailService;

        public AnalysisRequestService(
            ApplicationDbContext context,
            IAuditLogService auditLogService,
            IEmailService emailService)
        {
            _context = context;
            _auditLogService = auditLogService;
            _emailService = emailService;
        }

        // -------------------------------------------------------
        // Créer une nouvelle demande (brouillon ou soumise)
        // -------------------------------------------------------
        public async Task<RequestDetailDto> CreateAsync(string clientId, CreateRequestDto dto)
        {
            // Vérifier que le laboratoire existe
            if (!dto.IsDraft && dto.LaboratoryId > 0)
            {
                var lab = await _context.Laboratories.FindAsync(dto.LaboratoryId)
                    ?? throw new KeyNotFoundException("Laboratoire introuvable.");
            }

            // Vérification des doublons — même labo + mêmes échantillons + statut actif
            if (!dto.IsDraft && dto.LaboratoryId > 0 && dto.Samples.Any())
            {
                var newSamples = dto.Samples
                    .Select(s => new {
                        Type = s.Type.ToLower().Trim(),
                        Characteristics = s.Characteristics.ToLower().Trim(),
                        Quantity = s.Quantity,
                        Unit = s.Unit.ToLower().Trim()
                    })
                    .OrderBy(s => s.Type)
                    .ToList();

                var existingRequests = await _context.AnalysisRequests
                    .Include(r => r.Samples)
                    .Where(r =>
                        r.LaboratoryId == dto.LaboratoryId &&
                        (r.Status == RequestStatus.Submitted ||
                         r.Status == RequestStatus.Received ||
                         r.Status == RequestStatus.InProgress ||
                         r.Status == RequestStatus.InReview))
                    .ToListAsync();

                var isDuplicate = existingRequests.Any(r =>
                {
                    if (r.Samples.Count != dto.Samples.Count) return false;

                    var existingSamples = r.Samples
                        .Select(s => new {
                            Type = s.Type.ToLower().Trim(),
                            Characteristics = s.Characteristics.ToLower().Trim(),
                            Quantity = s.Quantity,
                            Unit = s.Unit.ToLower().Trim()
                        })
                        .OrderBy(s => s.Type)
                        .ToList();

                    return newSamples.Zip(existingSamples, (n, e) =>
                        n.Type == e.Type &&
                        n.Characteristics == e.Characteristics &&
                        n.Quantity == e.Quantity &&
                        n.Unit == e.Unit
                    ).All(match => match);
                });

                if (isDuplicate)
                    throw new ArgumentException(
                        "Une demande identique est déjà en cours de traitement pour ce laboratoire.");
            }

            // Créer la demande
            var request = new AnalysisRequest
            {
                ClientId = clientId,
                LaboratoryId = dto.LaboratoryId > 0 ? dto.LaboratoryId : 1, // valeur par défaut
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
                // Ignorer les échantillons vides pour les brouillons
                if (dto.IsDraft && string.IsNullOrEmpty(sampleDto.Type)) continue;
                
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
                        RecordedById = clientId
                    });
                }
            }

            await _context.SaveChangesAsync();

            // Notifier le client si la demande est soumise directement (pas un brouillon)
            if (!dto.IsDraft)
            {
                var client = await _context.Users.FindAsync(clientId);
                if (client != null)
                    await _emailService.SendRequestSubmittedAsync(
                        client.Email!, client.FirstName, request.Id);
            }

            await _auditLogService.LogAsync(
                request.Id, clientId,
                dto.IsDraft ? "Création du brouillon" : "Création et soumission",
                null,
                request.Status.ToString());

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
                .Include(r => r.Client)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            // Vérifier que la demande appartient bien au client qui la soumet
            if (request.ClientId != clientId)
                throw new UnauthorizedAccessException(
                    "Vous n'êtes pas autorisé à soumettre cette demande.");

            // Vérifier que la demande est bien en brouillon
            if (request.Status != RequestStatus.Draft)
                throw new ArgumentException("Seuls les brouillons peuvent être soumis.");

            // Vérifier qu'au moins un échantillon est présent
            if (!request.Samples.Any())
                throw new ArgumentException(
                    "La demande doit contenir au moins un échantillon.");

            // Passer en Submitted
            request.Status = RequestStatus.Submitted;
            request.IsDraft = false;
            request.SubmittedAt = DateTime.UtcNow;

            await _context.SaveChangesAsync();

            await _auditLogService.LogAsync(
                requestId, clientId,
                "Soumission de la demande",
                RequestStatus.Draft.ToString(),
                RequestStatus.Submitted.ToString());

            // Notifier le client que sa demande a été soumise
            await _emailService.SendRequestSubmittedAsync(
                request.Client.Email!, request.Client.FirstName, requestId);

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
        public async Task<RequestDetailDto> ReceiveAsync(int requestId, string receptionistId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Client)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.Status != RequestStatus.Submitted)
                throw new ArgumentException(
                    "Seules les demandes soumises peuvent être réceptionnées.");

            request.Status = RequestStatus.Received;
            request.ReceivedAt = DateTime.UtcNow;

            await _context.SaveChangesAsync();
            
            await _auditLogService.LogAsync(
                requestId, receptionistId,
                "Réception de la demande",
                RequestStatus.Submitted.ToString(),
                RequestStatus.Received.ToString());

            // Notifier le client que sa demande a été réceptionnée
            await _emailService.SendRequestReceivedAsync(
                request.Client.Email!, request.Client.FirstName, requestId);

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Assigner une demande à un laborantin (Réceptionniste)
        // -------------------------------------------------------
        public async Task<RequestDetailDto> AssignAsync(int requestId, string analystId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Client)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.Status != RequestStatus.Received)
                throw new ArgumentException(
                    "Seules les demandes réceptionnées peuvent être assignées.");

            request.AssignedToId = analystId;
            request.Status = RequestStatus.Assigned;

            await _context.SaveChangesAsync();

            await _auditLogService.LogAsync(
                requestId, "system",
                "Assignation de la demande",
                RequestStatus.Received.ToString(),
                RequestStatus.Assigned.ToString());

            // Notifier le client que sa demande a été assignée à un laborantin
            await _emailService.SendRequestAssignedAsync(
                request.Client.Email!, request.Client.FirstName, requestId);

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

            if (request.AssignedToId != analystId)
                throw new UnauthorizedAccessException(
                    "Vous n'êtes pas assigné à cette demande.");

            if (request.Status != RequestStatus.InProgress)
                throw new ArgumentException(
                    "La demande doit être en cours d'analyse pour saisir des résultats.");

            foreach (var resultDto in results)
            {
                var result = request.Samples
                    .SelectMany(s => s.Results)
                    .FirstOrDefault(r => r.Id == resultDto.ResultId)
                    ?? throw new KeyNotFoundException(
                        $"Résultat id={resultDto.ResultId} introuvable.");

                result.MeasuredValue = resultDto.MeasuredValue;
                result.RecordedById = analystId;
                result.RecordedAt = DateTime.UtcNow;

                // Calcul automatique de l'anomalie
                result.IsAnomaly = resultDto.MeasuredValue < result.LowerBound ||
                                   resultDto.MeasuredValue > result.UpperBound;
            }

            await _context.SaveChangesAsync();

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Marquer les analyses comme terminées (Laborantin)
        // -------------------------------------------------------
        public async Task<RequestDetailDto> CompleteAnalysisAsync(
            int requestId, string analystId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Samples)
                    .ThenInclude(s => s.Results)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.AssignedToId != analystId)
                throw new UnauthorizedAccessException(
                    "Vous n'êtes pas assigné à cette demande.");

            if (request.Status != RequestStatus.InProgress)
                throw new ArgumentException(
                    "La demande doit être en cours d'analyse.");

            var allResults = request.Samples.SelectMany(s => s.Results).ToList();
            if (allResults.Any(r => r.MeasuredValue == 0))
                throw new ArgumentException(
                    "Tous les résultats doivent être saisis avant de terminer.");

            request.Status = RequestStatus.InReview;

            await _context.SaveChangesAsync();

            await _auditLogService.LogAsync(
                requestId, analystId,
                "Analyses terminées — envoi au chef de labo",
                RequestStatus.InProgress.ToString(),
                RequestStatus.InReview.ToString());

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Valider les résultats (Chef de laboratoire)
        // -------------------------------------------------------
        public async Task<RequestDetailDto> ValidateAsync(
            int requestId, string labChiefId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Client)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.Status != RequestStatus.InReview)
                throw new ArgumentException(
                    "Seules les demandes en cours de révision peuvent être validées.");

            var oldStatus = request.Status.ToString();
            request.Status = RequestStatus.Validated;

            await _context.SaveChangesAsync();

            // Enregistrer dans l'historique
            await _auditLogService.LogAsync(
                requestId, labChiefId,
                "Validation des résultats",
                oldStatus,
                RequestStatus.Validated.ToString());

            // Notifier le client que ses résultats sont disponibles
            await _emailService.SendResultsReadyAsync(
                request.Client.Email!, request.Client.FirstName, requestId);

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Rejeter et renvoyer au laborantin (Chef de laboratoire)
        // La demande repasse en InProgress pour que le laborantin
        // corrige et resaisisse les résultats avant de renvoyer
        // à la validation
        // -------------------------------------------------------
        public async Task<RequestDetailDto> InvalidateAsync(
            int requestId, string labChiefId, string reason)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Client)
                .Include(r => r.Samples)
                    .ThenInclude(s => s.Results)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.Status != RequestStatus.InReview)
                throw new ArgumentException(
                    "Seules les demandes en cours de révision peuvent être rejetées.");

            var oldStatus = request.Status.ToString();

            // Repasser en InProgress — le même laborantin doit refaire l'analyse
            request.Status = RequestStatus.InProgress;
            request.Notes = string.IsNullOrEmpty(request.Notes)
                ? $"Rejet chef de labo : {reason}"
                : $"{request.Notes} | Rejet chef de labo : {reason}";

            // Remettre toutes les valeurs mesurées à 0
            // pour forcer le laborantin à tout resaisir
            foreach (var sample in request.Samples)
            {
                foreach (var result in sample.Results)
                {
                    result.MeasuredValue = 0;
                    result.IsAnomaly = false;
                    result.RecordedAt = DateTime.UtcNow;
                }
            }

            await _context.SaveChangesAsync();

            // Enregistrer dans l'historique
            await _auditLogService.LogAsync(
                requestId, labChiefId,
                "Rejet des résultats — renvoi au laborantin",
                oldStatus,
                RequestStatus.InProgress.ToString());

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
        // Définir les échéances d'une demande
        // -------------------------------------------------------
        public async Task<RequestDetailDto> SetDeadlinesAsync(
            int requestId, List<SetDeadlineDto> deadlines)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Deadlines)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            // Valider l'ordre chronologique par échantillon
                var bySample = deadlines.GroupBy(d => d.SampleId);
                foreach (var group in bySample)
                {
                    var ordered = group.OrderBy(d => GetPhaseOrder(d.Phase)).ToList();
                    for (int i = 1; i < ordered.Count; i++)
                    {
                        if (ordered[i].PlannedDate <= ordered[i - 1].PlannedDate)
                        {
                            throw new ArgumentException(
                                $"L'échéance '{ordered[i].Phase}' doit être postérieure " +
                                $"à '{ordered[i - 1].Phase}'.");
                        }
                    }
                }

            foreach (var deadlineDto in deadlines)
            {
                if (!Enum.TryParse<DeadlinePhase>(deadlineDto.Phase, true, out var phase))
                    throw new ArgumentException($"Phase invalide : {deadlineDto.Phase}");

                if (deadlineDto.PlannedDate <= DateTime.UtcNow)
                    throw new ArgumentException(
                        $"La date pour la phase {deadlineDto.Phase} doit être dans le futur.");

                // Chercher une échéance existante pour cette phase + cet échantillon
                var existing = request.Deadlines
                    .FirstOrDefault(d => d.Phase == phase &&
                                        d.SampleId == deadlineDto.SampleId);

                if (existing != null)
                {
                    existing.PlannedDate = deadlineDto.PlannedDate;
                    existing.IsOverdue = false;
                }
                else
                {
                    _context.Deadlines.Add(new Deadline
                    {
                        RequestId = requestId,
                        SampleId    = deadlineDto.SampleId,
                        Phase = phase,
                        PlannedDate = deadlineDto.PlannedDate,
                        IsOverdue = false
                    });
                }
            }

            await _context.SaveChangesAsync();

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Récupérer les échéances d'une demande
        // -------------------------------------------------------
        public async Task<List<DeadlineDto>> GetDeadlinesAsync(int requestId)
        {
            var deadlines = await _context.Deadlines
                .Include(d => d.Sample)
                .Where(d => d.RequestId == requestId)
                .OrderBy(d => d.SampleId)
                .ThenBy(d => d.Phase)
                .ToListAsync();

            return deadlines.Select(d => new DeadlineDto
            {
                Id = d.Id,
                Phase = d.Phase.ToString(),
                PlannedDate = d.PlannedDate,
                ActualDate = d.ActualDate,
                IsOverdue = d.IsOverdue,
                SampleId = d.SampleId,
                SampleType = d.Sample?.Type ?? ""
            }).ToList();
        }

        // -------------------------------------------------------
        // Méthodes privées de mapping Model → DTO
        // -------------------------------------------------------
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

        private static int GetPhaseOrder(string phase) => phase switch
        {
            "Reception"      => 1,
            "Assignment"     => 2,
            "Analysis"       => 3,
            "Validation"     => 4,
            "ResultDelivery" => 5,
            _                => 99
        };

        private static RequestDetailDto MapToDetailDto(AnalysisRequest r) => new()
        {
            Id = r.Id,
            Status = r.Status.ToString(),
            Notes = r.Notes,
            IsDraft = r.IsDraft,
            CreatedAt = r.CreatedAt,
            ReceivedAt = r.ReceivedAt,
            SubmittedAt = r.SubmittedAt,
            LaboratoryId   = r.LaboratoryId,
            LaboratoryName = r.Laboratory?.Name ?? "",
            ClientId = r.ClientId,
            ClientName = $"{r.Client?.FirstName} {r.Client?.LastName}",
            ClientEmail = r.Client?.Email ?? "",
            AssignedToId = r.AssignedToId,
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
                    AnalysisTypeId   = res.AnalysisTypeId,
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

        // -------------------------------------------------------
        // Modifier une demande existante
        // Uniquement possible si la demande est en statut Draft
        // -------------------------------------------------------
        public async Task<RequestDetailDto> UpdateAsync(
            int requestId, string userId, UpdateRequestDto dto)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Samples)
                    .ThenInclude(s => s.Results)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.ClientId != userId)
                throw new UnauthorizedAccessException(
                    "Vous n'êtes pas autorisé à modifier cette demande.");

            // Vérifier que la demande est en brouillon
            if (request.Status != RequestStatus.Draft)
                throw new ArgumentException(
                    "Seules les demandes en brouillon peuvent être modifiées.");

            // Vérifier que le laboratoire existe
            if (dto.LaboratoryId > 0)
            {
                var lab = await _context.Laboratories.FindAsync(dto.LaboratoryId)
                    ?? throw new KeyNotFoundException("Laboratoire introuvable.");
                request.LaboratoryId = dto.LaboratoryId;
            }

            // Mettre à jour les infos de base
            request.Notes = dto.Notes;
            request.IsDraft = dto.IsDraft;
            request.Status = dto.IsDraft
                ? RequestStatus.Draft
                : RequestStatus.Submitted;

            if (!dto.IsDraft)
                request.SubmittedAt = DateTime.UtcNow;

            // Supprimer les anciens échantillons et résultats
            var oldResults = request.Samples
                .SelectMany(s => s.Results).ToList();
            _context.AnalysisResults.RemoveRange(oldResults);
            _context.Samples.RemoveRange(request.Samples);
            await _context.SaveChangesAsync();

            // Recréer les nouveaux échantillons
            foreach (var sampleDto in dto.Samples)
            {
                if (dto.IsDraft && string.IsNullOrEmpty(sampleDto.Type)) continue;
                
                var sample = new Sample
                {
                    RequestId = requestId,
                    Type = sampleDto.Type,
                    Characteristics = sampleDto.Characteristics,
                    Quantity = sampleDto.Quantity,
                    Unit = sampleDto.Unit
                };
                _context.Samples.Add(sample);
                await _context.SaveChangesAsync();

                foreach (var analysisTypeId in sampleDto.AnalysisTypeIds)
                {
                    var analysisType = await _context.AnalysisTypes
                        .FindAsync(analysisTypeId);
                    if (analysisType == null) continue;

                    _context.AnalysisResults.Add(new AnalysisResult
                    {
                        SampleId = sample.Id,
                        AnalysisTypeId = analysisTypeId,
                        LowerBound = analysisType.ReferenceMin,
                        UpperBound = analysisType.ReferenceMax,
                        RecordedById = userId
                    });
                }
            }

            await _context.SaveChangesAsync();

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Laborantin accepte la demande assignée
        // La demande passe en InProgress — analyses en cours
        // -------------------------------------------------------
        public async Task<RequestDetailDto> AnalystAcceptAsync(
            int requestId, string analystId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Client)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            // Vérifier que la demande est bien assignée à ce laborantin
            if (request.AssignedToId != analystId)
                throw new UnauthorizedAccessException(
                    "Cette demande ne vous est pas assignée.");

            // Vérifier que la demande est en attente d'acceptation
            if (request.Status != RequestStatus.Assigned)
                throw new ArgumentException(
                    "Seules les demandes assignées peuvent être acceptées.");

            // passe en InProgress après acceptation de la demande par le laborantin
            request.Status = RequestStatus.InProgress;

            await _context.SaveChangesAsync();

            // Enregistrer l'acceptation dans l'historique
            await _auditLogService.LogAsync(
                requestId, analystId,
                "Acceptation par le laborantin",
                RequestStatus.Assigned.ToString(),
                RequestStatus.InProgress.ToString());

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Laborantin refuse la demande assignée
        // La demande est automatiquement clôturée selon le workflow
        // -------------------------------------------------------
        public async Task<RequestDetailDto> AnalystRejectAsync(
            int requestId, string analystId, string reason)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Client)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            // Vérifier que la demande est bien assignée à ce laborantin
            if (request.AssignedToId != analystId)
                throw new UnauthorizedAccessException(
                    "Cette demande ne vous est pas assignée.");

            // Vérifier que la demande est en cours (assignée)
            if (request.Status != RequestStatus.Assigned)
                throw new ArgumentException(
                    "Seules les demandes assignées peuvent être refusées.");

            var oldStatus = request.Status.ToString();

            // Clôturer automatiquement la demande
            request.Status = RequestStatus.Closed;
            request.Notes = string.IsNullOrEmpty(request.Notes)
                ? $"Refus laborantin : {reason}"
                : $"{request.Notes} | Refus laborantin : {reason}";

            await _context.SaveChangesAsync();

            // Enregistrer dans l'historique
            await _auditLogService.LogAsync(
                requestId, analystId,
                "Refus par le laborantin",
                oldStatus,
                RequestStatus.Closed.ToString());

            // Notifier le client du refus
            await _emailService.SendRequestRejectedAsync(
                request.Client.Email!,
                request.Client.FirstName,
                requestId,
                reason);

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Supprimer une demande en brouillon
        // -------------------------------------------------------
        public async Task DeleteAsync(int requestId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Samples)
                    .ThenInclude(s => s.Results)
                .Include(r => r.Deadlines)
                .Include(r => r.AuditLogs)
                .Include(r => r.Notifications)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            // Supprimer les entités liées dans l'ordre
            _context.AnalysisResults.RemoveRange(
                request.Samples.SelectMany(s => s.Results));
            _context.Samples.RemoveRange(request.Samples);
            _context.Deadlines.RemoveRange(request.Deadlines);
            _context.AuditLogs.RemoveRange(request.AuditLogs);
            _context.Notifications.RemoveRange(request.Notifications);
            _context.AnalysisRequests.Remove(request);

            await _context.SaveChangesAsync();
        }

        public async Task DeleteDeadlineAsync(int deadlineId)
        {
            var deadline = await _context.Deadlines.FindAsync(deadlineId)
                ?? throw new KeyNotFoundException("Échéance introuvable.");
            _context.Deadlines.Remove(deadline);
            await _context.SaveChangesAsync();
        }
    }
}