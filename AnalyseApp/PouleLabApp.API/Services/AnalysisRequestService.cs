using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.Data;
using PouleLabApp.API.DTOs.Request;
using PouleLabApp.API.Models;
using PouleLabApp.API.Services.Interfaces;

namespace PouleLabApp.API.Services
{
    public class AnalysisRequestService : IAnalysisRequestService
    {
        private readonly ApplicationDbContext _context;
        private readonly IAuditLogService _auditLogService;
        private readonly IEmailService _emailService;
        private readonly UserManager<ApplicationUser> _userManager;

        public AnalysisRequestService(
            ApplicationDbContext context,
            IAuditLogService auditLogService,
            IEmailService emailService,
            UserManager<ApplicationUser> userManager)
        {
            _context         = context;
            _auditLogService = auditLogService;
            _emailService    = emailService;
            _userManager     = userManager;
        }

        // -------------------------------------------------------
        // Notifications
        // -------------------------------------------------------
        private async Task CreateNotificationAsync(
            string recipientId, int requestId, string message)
        {
            _context.Notifications.Add(new Notification
            {
                RecipientId = recipientId,
                RequestId   = requestId,
                Message     = message,
                IsRead      = false,
                CreatedAt   = DateTime.UtcNow
            });
            await _context.SaveChangesAsync();
        }

        private async Task NotifyRoleAsync(
            string role, int requestId, string message, int? laboratoryId = null)
        {
            var users = await _userManager.GetUsersInRoleAsync(role);
            var filtered = users.Where(u => u.IsActive);

            // ← Filtrer par labo pour les rôles staff
            if (laboratoryId.HasValue &&
                new[] { "Receptionist", "Analyst", "LabChief" }.Contains(role))
                filtered = filtered.Where(u => u.LaboratoryId == laboratoryId);

            foreach (var user in filtered)
                await CreateNotificationAsync(user.Id, requestId, message);
        }

        // -------------------------------------------------------
        // Créer une nouvelle demande
        // -------------------------------------------------------
        public async Task<RequestDetailDto> CreateAsync(
            string clientId, CreateRequestDto dto)
        {
            if (!dto.IsDraft && dto.LaboratoryId > 0)
            {
                _ = await _context.Laboratories.FindAsync(dto.LaboratoryId)
                    ?? throw new KeyNotFoundException("Laboratoire introuvable.");
            }

            if (!dto.IsDraft && dto.LaboratoryId > 0 && dto.Samples.Any())
            {
                var newSamples = dto.Samples
                    .Select(s => new {
                        Type            = s.Type.ToLower().Trim(),
                        Characteristics = s.Characteristics.ToLower().Trim(),
                        Quantity        = s.Quantity,
                        Unit            = s.Unit.ToLower().Trim()
                    })
                    .OrderBy(s => s.Type)
                    .ToList();

                var existingRequests = await _context.AnalysisRequests
                    .Include(r => r.Samples)
                    .Where(r =>
                        r.LaboratoryId == dto.LaboratoryId &&
                        (r.Status == RequestStatus.Submitted  ||
                         r.Status == RequestStatus.Received   ||
                         r.Status == RequestStatus.InProgress ||
                         r.Status == RequestStatus.InReview))
                    .ToListAsync();

                var isDuplicate = existingRequests.Any(r =>
                {
                    if (r.Samples.Count != dto.Samples.Count) return false;
                    var existingSamples = r.Samples
                        .Select(s => new {
                            Type            = s.Type.ToLower().Trim(),
                            Characteristics = s.Characteristics.ToLower().Trim(),
                            Quantity        = s.Quantity,
                            Unit            = s.Unit.ToLower().Trim()
                        })
                        .OrderBy(s => s.Type)
                        .ToList();

                    return newSamples.Zip(existingSamples, (n, e) =>
                        n.Type == e.Type && n.Characteristics == e.Characteristics &&
                        n.Quantity == e.Quantity && n.Unit == e.Unit
                    ).All(match => match);
                });

                if (isDuplicate)
                    throw new ArgumentException(
                        "Une demande identique est déjà en cours de traitement pour ce laboratoire.");
            }

            var request = new AnalysisRequest
            {
                ClientId     = clientId,
                LaboratoryId = dto.LaboratoryId > 0 ? dto.LaboratoryId : 1,
                Brand        = dto.Brand,
                Notes        = dto.Notes,
                IsDraft      = dto.IsDraft,
                Status       = dto.IsDraft ? RequestStatus.Draft : RequestStatus.Submitted,
                CreatedAt    = DateTime.UtcNow,
                SubmittedAt  = dto.IsDraft ? default : DateTime.UtcNow
            };

            _context.AnalysisRequests.Add(request);
            await _context.SaveChangesAsync();

            foreach (var sampleDto in dto.Samples)
            {
                if (dto.IsDraft && string.IsNullOrEmpty(sampleDto.Type)) continue;

                var sample = new Sample
                {
                    RequestId       = request.Id,
                    Type            = sampleDto.Type,
                    Characteristics = sampleDto.Characteristics,
                    Quantity        = sampleDto.Quantity,
                    Unit            = sampleDto.Unit
                };
                _context.Samples.Add(sample);
                await _context.SaveChangesAsync();

                foreach (var analysisName in sampleDto.AnalysisNames
                        .Where(n => !string.IsNullOrWhiteSpace(n)))
                {
                    _context.AnalysisResults.Add(new AnalysisResult
                    {
                        SampleId     = sample.Id,
                        AnalysisName = analysisName.Trim(),
                        RecordedById = clientId
                    });
                }

                // ← Créer la deadline/urgence associée à cet échantillon
                _context.Deadlines.Add(new Deadline
                {
                    RequestId          = request.Id,
                    SampleId           = sample.Id,
                    IsPerishable       = sampleDto.IsPerishable,
                    ExpiryDate         = sampleDto.IsPerishable ? sampleDto.ExpiryDate : null,
                    UrgencyLevel       = string.IsNullOrEmpty(sampleDto.UrgencyLevel)
                                          ? "Normal" : sampleDto.UrgencyLevel,
                    UrgencyDescription = sampleDto.UrgencyDescription ?? string.Empty
                });
            }

            await _context.SaveChangesAsync();

            if (!dto.IsDraft)
            {
                var client = await _context.Users.FindAsync(clientId);
                if (client != null)
                    await _emailService.SendRequestSubmittedAsync(
                        client.Email!, client.FirstName, request.Id);

                await NotifyRoleAsync("Receptionist", request.Id,
                    $"Nouvelle demande #{request.Id}...", request.LaboratoryId);
                await NotifyRoleAsync("Administrator", request.Id,
                    $"Nouvelle demande #{request.Id}...");
                await NotifyRoleAsync("Manager", request.Id,
                    $"Nouvelle demande #{request.Id}...");
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
        public async Task<RequestDetailDto> SubmitAsync(
            int requestId, string clientId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Samples)
                .Include(r => r.Client)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.ClientId != clientId)
                throw new UnauthorizedAccessException(
                    "Vous n'êtes pas autorisé à soumettre cette demande.");

            if (request.Status != RequestStatus.Draft)
                throw new ArgumentException("Seuls les brouillons peuvent être soumis.");

            if (!request.Samples.Any())
                throw new ArgumentException(
                    "La demande doit contenir au moins un échantillon.");

            request.Status      = RequestStatus.Submitted;
            request.IsDraft     = false;
            request.SubmittedAt = DateTime.UtcNow;

            await _context.SaveChangesAsync();

            await _auditLogService.LogAsync(
                requestId, clientId,
                "Soumission de la demande",
                RequestStatus.Draft.ToString(),
                RequestStatus.Submitted.ToString());

            await _emailService.SendRequestSubmittedAsync(
                request.Client.Email!, request.Client.FirstName, requestId);

            await NotifyRoleAsync("Receptionist", request.Id,
                $"Nouvelle demande #{request.Id}...", request.LaboratoryId);
            await NotifyRoleAsync("Administrator", request.Id,
                $"Nouvelle demande #{request.Id}...");
            await NotifyRoleAsync("Manager", request.Id,
                $"Nouvelle demande #{request.Id}...");

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Récupérer une demande par son ID
        // -------------------------------------------------------
        public async Task<RequestDetailDto?> GetByIdAsync(int requestId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Client)
                .Include(r => r.AssignedTo)
                .Include(r => r.Laboratory)
                .Include(r => r.Samples)
                    .ThenInclude(s => s.Results)
                .Include(r => r.Deadlines) // ← inclure les deadlines
                .FirstOrDefaultAsync(r => r.Id == requestId);

            if (request == null) return null;
            return MapToDetailDto(request);
        }

        // -------------------------------------------------------
        // Récupérer toutes les demandes
        // -------------------------------------------------------
        public async Task<List<RequestListDto>> GetAllAsync(
            string? status = null, int? laboratoryId = null) {
            var query = _context.AnalysisRequests
                .Include(r => r.Client)
                .Include(r => r.Laboratory)
                .Include(r => r.Samples)
                .AsQueryable();

            if (laboratoryId.HasValue)
            {
                query = query.Where(r => r.LaboratoryId == laboratoryId.Value);
            }

            if (!string.IsNullOrEmpty(status) &&
                Enum.TryParse<RequestStatus>(status, true, out var parsedStatus))
                query = query.Where(r => r.Status == parsedStatus);

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
        // Réceptionner une demande
        // -------------------------------------------------------
        public async Task<RequestDetailDto> ReceiveAsync(
            int requestId, string receptionistId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Client)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.Status != RequestStatus.Submitted)
                throw new ArgumentException(
                    "Seules les demandes soumises peuvent être réceptionnées.");

            request.Status     = RequestStatus.Received;
            request.ReceivedAt = DateTime.UtcNow;

            await _context.SaveChangesAsync();

            await _auditLogService.LogAsync(
                requestId, receptionistId,
                "Réception de la demande",
                RequestStatus.Submitted.ToString(),
                RequestStatus.Received.ToString());

            await _emailService.SendRequestReceivedAsync(
                request.Client.Email!, request.Client.FirstName, requestId);

            await CreateNotificationAsync(request.ClientId, requestId,
                $"Votre demande #{requestId} a été réceptionnée et est en cours de traitement.");

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Assigner une demande à un laborantin
        // -------------------------------------------------------
        public async Task<RequestDetailDto> AssignAsync(
            int requestId, string analystId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Client)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.Status != RequestStatus.Received)
                throw new ArgumentException(
                    "Seules les demandes réceptionnées peuvent être assignées.");

            request.AssignedToId = analystId;
            request.Status       = RequestStatus.Assigned;

            await _context.SaveChangesAsync();

            await _auditLogService.LogAsync(
                requestId, analystId,
                "Assignation de la demande",
                RequestStatus.Received.ToString(),
                RequestStatus.Assigned.ToString());

            await _emailService.SendRequestAssignedAsync(
                request.Client.Email!, request.Client.FirstName, requestId);

            await CreateNotificationAsync(analystId, requestId,
                $"La demande #{requestId} vous a été assignée. Veuillez l'accepter ou la refuser.");
            await CreateNotificationAsync(request.ClientId, requestId,
                $"Votre demande #{requestId} a été assignée à un laborantin.");

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Saisir les résultats d'analyse
        // -------------------------------------------------------
        public async Task<RequestDetailDto> SaveResultsAsync(
            int requestId, string analystId, List<SaveResultDto> results)
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

            foreach (var resultDto in results)
            {
                var result = request.Samples
                    .SelectMany(s => s.Results)
                    .FirstOrDefault(r => r.Id == resultDto.ResultId)
                    ?? throw new KeyNotFoundException(
                        $"Résultat id={resultDto.ResultId} introuvable.");

                result.MeasuredValue = resultDto.MeasuredValue;
                result.LowerBound    = resultDto.LowerBound;
                result.UpperBound    = resultDto.UpperBound;
                result.Unit          = resultDto.Unit;
                result.RecordedById  = analystId;
                result.RecordedAt    = DateTime.UtcNow;
                result.IsAnomaly     = resultDto.MeasuredValue < resultDto.LowerBound ||
                                       resultDto.MeasuredValue > resultDto.UpperBound;
            }

            await _context.SaveChangesAsync();

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur.");
        }

        // -------------------------------------------------------
        // Terminer les analyses
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
            if (allResults.Any(r => r.MeasuredValue == 0 && r.LowerBound == 0))
                throw new ArgumentException(
                    "Tous les résultats doivent être saisis avant de terminer.");

            request.Status = RequestStatus.InReview;

            await _context.SaveChangesAsync();

            await _auditLogService.LogAsync(
                requestId, analystId,
                "Analyses terminées — envoi au chef de labo",
                RequestStatus.InProgress.ToString(),
                RequestStatus.InReview.ToString());

            await NotifyRoleAsync("LabChief", requestId,
                $"La demande #{requestId} est prête pour validation.",
                request.LaboratoryId);

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Valider les résultats
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

            var oldStatus  = request.Status.ToString();
            request.Status = RequestStatus.Validated;

            await _context.SaveChangesAsync();

            await _auditLogService.LogAsync(
                requestId, labChiefId,
                "Validation des résultats",
                oldStatus,
                RequestStatus.Validated.ToString());

            await _emailService.SendResultsReadyAsync(
                request.Client.Email!, request.Client.FirstName, requestId);

            await CreateNotificationAsync(request.ClientId, requestId,
                $"✓ Votre demande #{requestId} a été validée. Le bulletin est disponible en téléchargement.");

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Rejeter et renvoyer au laborantin
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

            var oldStatus  = request.Status.ToString();
            request.Status = RequestStatus.InProgress;
            request.Notes  = string.IsNullOrEmpty(request.Notes)
                ? $"Rejet chef de labo : {reason}"
                : $"{request.Notes} | Rejet chef de labo : {reason}";

            foreach (var sample in request.Samples)
                foreach (var result in sample.Results)
                {
                    result.MeasuredValue = 0;
                    result.IsAnomaly     = false;
                    result.RecordedAt    = DateTime.UtcNow;
                }

            await _context.SaveChangesAsync();

            await _auditLogService.LogAsync(
                requestId, labChiefId,
                "Rejet des résultats — renvoi au laborantin",
                oldStatus,
                RequestStatus.InProgress.ToString());

            if (!string.IsNullOrEmpty(request.AssignedToId))
                await CreateNotificationAsync(request.AssignedToId, requestId,
                    $"⚠ Les résultats de la demande #{requestId} ont été rejetés : {reason}. Veuillez corriger et renvoyer.");

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Laborantin accepte la demande
        // -------------------------------------------------------
        public async Task<RequestDetailDto> AnalystAcceptAsync(
            int requestId, string analystId)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Client)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.AssignedToId != analystId)
                throw new UnauthorizedAccessException(
                    "Cette demande ne vous est pas assignée.");

            if (request.Status != RequestStatus.Assigned)
                throw new ArgumentException(
                    "Seules les demandes assignées peuvent être acceptées.");

            request.Status = RequestStatus.InProgress;

            await _context.SaveChangesAsync();

            await _auditLogService.LogAsync(
                requestId, analystId,
                "Acceptation par le laborantin",
                RequestStatus.Assigned.ToString(),
                RequestStatus.InProgress.ToString());

            await CreateNotificationAsync(request.ClientId, requestId,
                $"Votre demande #{requestId} a été acceptée par le laborantin et est en cours d'analyse.");

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Laborantin refuse la demande
        // -------------------------------------------------------
        public async Task<RequestDetailDto> AnalystRejectAsync(
            int requestId, string analystId, string reason)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Client)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            if (request.AssignedToId != analystId)
                throw new UnauthorizedAccessException(
                    "Cette demande ne vous est pas assignée.");

            if (request.Status != RequestStatus.Assigned)
                throw new ArgumentException(
                    "Seules les demandes assignées peuvent être refusées.");

            var oldStatus  = request.Status.ToString();
            request.Status = RequestStatus.Closed;
            request.Notes  = string.IsNullOrEmpty(request.Notes)
                ? $"Refus laborantin : {reason}"
                : $"{request.Notes} | Refus laborantin : {reason}";

            await _context.SaveChangesAsync();

            await _auditLogService.LogAsync(
                requestId, analystId,
                "Refus par le laborantin",
                oldStatus,
                RequestStatus.Closed.ToString());

            await _emailService.SendRequestRejectedAsync(
                request.Client.Email!, request.Client.FirstName, requestId, reason);

            await CreateNotificationAsync(request.ClientId, requestId,
                $"Votre demande #{requestId} a été refusée par le laborantin : {reason}.");
            await NotifyRoleAsync("Receptionist", requestId,
                $"La demande #{requestId} a été refusée par le laborantin. Une réassignation peut être nécessaire.");

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur lors de la récupération de la demande.");
        }

        // -------------------------------------------------------
        // Récupérer l'historique
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
                Id          = a.Id,
                Action      = a.Action,
                PerformedBy = $"{a.PerformedBy?.FirstName} {a.PerformedBy?.LastName}",
                OldValue    = a.OldValue,
                NewValue    = a.NewValue,
                PerformedAt = a.PerformedAt
            }).ToList();
        }

        // -------------------------------------------------------
        // Définir les échéances (depuis le détail)
        // -------------------------------------------------------
        public async Task<RequestDetailDto> SetDeadlinesAsync(
            int requestId, List<SetDeadlineDto> deadlines)
        {
            var request = await _context.AnalysisRequests
                .Include(r => r.Deadlines)
                .FirstOrDefaultAsync(r => r.Id == requestId)
                ?? throw new KeyNotFoundException("Demande introuvable.");

            foreach (var dto in deadlines)
            {
                var existing = request.Deadlines
                    .FirstOrDefault(d => d.SampleId == dto.SampleId);

                if (existing != null)
                {
                    existing.IsPerishable       = dto.IsPerishable;
                    existing.ExpiryDate         = dto.ExpiryDate;
                    existing.UrgencyLevel       = dto.UrgencyLevel;
                    existing.UrgencyDescription = dto.UrgencyDescription;
                }
                else
                {
                    _context.Deadlines.Add(new Deadline
                    {
                        RequestId          = requestId,
                        SampleId           = dto.SampleId,
                        IsPerishable       = dto.IsPerishable,
                        ExpiryDate         = dto.ExpiryDate,
                        UrgencyLevel       = dto.UrgencyLevel,
                        UrgencyDescription = dto.UrgencyDescription
                    });
                }
            }

            await _context.SaveChangesAsync();

            return await GetByIdAsync(requestId)
                ?? throw new Exception("Erreur.");
        }

        // -------------------------------------------------------
        // Récupérer les échéances
        // -------------------------------------------------------
        public async Task<List<DeadlineDto>> GetDeadlinesAsync(int requestId)
        {
            var deadlines = await _context.Deadlines
                .Include(d => d.Sample)
                .Where(d => d.RequestId == requestId)
                .OrderBy(d => d.SampleId)
                .ToListAsync();

            return deadlines.Select(d => new DeadlineDto
            {
                Id                 = d.Id,
                SampleId           = d.SampleId,
                SampleType         = d.Sample?.Type ?? "",
                IsPerishable       = d.IsPerishable,
                ExpiryDate         = d.ExpiryDate,
                UrgencyLevel       = d.UrgencyLevel,
                UrgencyDescription = d.UrgencyDescription
            }).ToList();
        }

        // -------------------------------------------------------
        // Modifier une demande (brouillon)
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

            if (request.Status != RequestStatus.Draft)
                throw new ArgumentException(
                    "Seules les demandes en brouillon peuvent être modifiées.");

            if (dto.LaboratoryId > 0)
            {
                _ = await _context.Laboratories.FindAsync(dto.LaboratoryId)
                    ?? throw new KeyNotFoundException("Laboratoire introuvable.");
                request.LaboratoryId = dto.LaboratoryId;
            }

            request.Notes   = dto.Notes;
            request.Brand   = dto.Brand;
            request.IsDraft = dto.IsDraft;
            request.Status  = dto.IsDraft ? RequestStatus.Draft : RequestStatus.Submitted;

            if (!dto.IsDraft)
                request.SubmittedAt = DateTime.UtcNow;

            // ← Sauvegarder l'urgence existante par type d'échantillon
            var urgencyByType = new Dictionary<string, Deadline>();
            foreach (var sample in request.Samples)
            {
                var deadline = await _context.Deadlines
                    .FirstOrDefaultAsync(d => d.SampleId == sample.Id);
                if (deadline != null)
                    urgencyByType[sample.Type.ToLower()] = deadline;
            }

            // ← Supprimer deadlines, résultats et échantillons
            var sampleIds = request.Samples.Select(s => s.Id).ToList();
            var relatedDeadlines = await _context.Deadlines
                .Where(d => sampleIds.Contains(d.SampleId))
                .ToListAsync();
            _context.Deadlines.RemoveRange(relatedDeadlines);

            var oldResults = request.Samples.SelectMany(s => s.Results).ToList();
            _context.AnalysisResults.RemoveRange(oldResults);
            _context.Samples.RemoveRange(request.Samples);
            await _context.SaveChangesAsync();

            foreach (var sampleDto in dto.Samples)
            {
                if (dto.IsDraft && string.IsNullOrEmpty(sampleDto.Type)) continue;

                var sample = new Sample
                {
                    RequestId       = requestId,
                    Type            = sampleDto.Type,
                    Characteristics = sampleDto.Characteristics,
                    Quantity        = sampleDto.Quantity,
                    Unit            = sampleDto.Unit
                };
                _context.Samples.Add(sample);
                await _context.SaveChangesAsync();

                foreach (var analysisName in sampleDto.AnalysisNames
                        .Where(n => !string.IsNullOrWhiteSpace(n)))
                {
                    _context.AnalysisResults.Add(new AnalysisResult
                    {
                        SampleId     = sample.Id,
                        AnalysisName = analysisName.Trim(),
                        RecordedById = userId
                    });
                }

                // ← Urgence : utiliser celle du DTO, ou restaurer l'ancienne
                var existingUrgency = urgencyByType.GetValueOrDefault(sampleDto.Type.ToLower());
                _context.Deadlines.Add(new Deadline
                {
                    RequestId          = requestId,
                    SampleId           = sample.Id,
                    IsPerishable       = sampleDto.IsPerishable != default
                                          ? sampleDto.IsPerishable
                                          : existingUrgency?.IsPerishable ?? false,
                    ExpiryDate         = sampleDto.ExpiryDate
                                          ?? existingUrgency?.ExpiryDate,
                    UrgencyLevel       = !string.IsNullOrEmpty(sampleDto.UrgencyLevel)
                                          ? sampleDto.UrgencyLevel
                                          : existingUrgency?.UrgencyLevel ?? "Normal",
                    UrgencyDescription = !string.IsNullOrEmpty(sampleDto.UrgencyDescription)
                                          ? sampleDto.UrgencyDescription
                                          : existingUrgency?.UrgencyDescription ?? string.Empty
                });
            }

            await _context.SaveChangesAsync();

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

            if (request.Status != RequestStatus.Draft &&
                request.Status != RequestStatus.Submitted)
                throw new ArgumentException(
                    "Seules les demandes en brouillon ou soumises " +
                    "(non encore réceptionnées) peuvent être supprimées.");

            _context.AnalysisResults.RemoveRange(
                request.Samples.SelectMany(s => s.Results));
                _context.Deadlines.RemoveRange(request.Deadlines);
            _context.Samples.RemoveRange(request.Samples);
            _context.AuditLogs.RemoveRange(request.AuditLogs);
            _context.Notifications.RemoveRange(request.Notifications);
            _context.AnalysisRequests.Remove(request);

            await _context.SaveChangesAsync();
        }

        // -------------------------------------------------------
        // Supprimer une échéance individuelle
        // -------------------------------------------------------
        public async Task DeleteDeadlineAsync(int deadlineId)
        {
            var deadline = await _context.Deadlines.FindAsync(deadlineId)
                ?? throw new KeyNotFoundException("Échéance introuvable.");
            _context.Deadlines.Remove(deadline);
            await _context.SaveChangesAsync();
        }

        // -------------------------------------------------------
        // Mappings Model → DTO
        // -------------------------------------------------------
        private static RequestListDto MapToListDto(AnalysisRequest r) => new()
        {
            Id             = r.Id,
            Status         = r.Status.ToString(),
            LaboratoryName = r.Laboratory?.Name ?? "",
            ClientName     = $"{r.Client?.FirstName} {r.Client?.LastName}",
            CreatedAt      = r.CreatedAt,
            ReceivedAt     = r.ReceivedAt,
            IsDraft        = r.IsDraft,
            SamplesCount   = r.Samples?.Count ?? 0
        };

        private static RequestDetailDto MapToDetailDto(AnalysisRequest r) => new()
        {
            Id             = r.Id,
            Status         = r.Status.ToString(),
            Brand          = r.Brand,
            Notes          = r.Notes,
            IsDraft        = r.IsDraft,
            CreatedAt      = r.CreatedAt,
            ReceivedAt     = r.ReceivedAt,
            SubmittedAt    = r.SubmittedAt,
            LaboratoryId   = r.LaboratoryId,
            LaboratoryName = r.Laboratory?.Name ?? "",
            ClientId       = r.ClientId,
            ClientName     = $"{r.Client?.FirstName} {r.Client?.LastName}",
            ClientEmail    = r.Client?.Email ?? "",
            AssignedToId   = r.AssignedToId,
            AssignedToName = r.AssignedTo != null
                ? $"{r.AssignedTo.FirstName} {r.AssignedTo.LastName}"
                : null,
            Samples = r.Samples?.Select(s =>
            {
                var deadline = r.Deadlines?.FirstOrDefault(d => d.SampleId == s.Id);
                return new SampleDetailDto
                {
                    Id              = s.Id,
                    Type            = s.Type,
                    Characteristics = s.Characteristics,
                    Quantity        = s.Quantity,
                    Unit            = s.Unit,
                    Results         = s.Results?.Select(res => new AnalysisResultDetailDto
                    {
                        Id            = res.Id,
                        AnalysisName  = res.AnalysisName,
                        MeasuredValue = res.MeasuredValue,
                        LowerBound    = res.LowerBound,
                        UpperBound    = res.UpperBound,
                        Unit          = res.Unit,
                        IsAnomaly     = res.IsAnomaly,
                        RecordedAt    = res.RecordedAt
                    }).ToList() ?? new(),
                    IsPerishable       = deadline?.IsPerishable ?? false,
                    ExpiryDate         = deadline?.ExpiryDate,
                    UrgencyLevel       = deadline?.UrgencyLevel ?? "Normal",
                    UrgencyDescription = deadline?.UrgencyDescription ?? string.Empty
                };
            }).ToList() ?? new()
        };
    }
}