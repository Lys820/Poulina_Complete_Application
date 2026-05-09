using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using PouleLabApp.API.DTOs.Request;
using PouleLabApp.API.Models;
using PouleLabApp.API.Services.Interfaces;

namespace PouleLabApp.API.Controllers
{
    [ApiController]
    [Route("api/requests")]
    [Authorize]
    public class AnalysisRequestController : ControllerBase
    {
        private readonly IAnalysisRequestService _requestService;
        private readonly UserManager<ApplicationUser> _userManager;

        public AnalysisRequestController(
            IAnalysisRequestService requestService,
            UserManager<ApplicationUser> userManager)
        {
            _requestService = requestService;
            _userManager = userManager;
        }

        // -------------------------------------------------------
        // POST /api/requests
        // Créer une demande — uniquement Client, Manager, Admin
        // Receptionist, Analyst, LabChief ne peuvent pas créer
        // -------------------------------------------------------
        [HttpPost]
        [Authorize(Policy = "RequireClientRole")]
        public async Task<IActionResult> Create([FromBody] CreateRequestDto dto)
        {
            var clientId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            if (clientId == null)
                return Unauthorized(new { message = "Utilisateur non identifié." });

            var result = await _requestService.CreateAsync(clientId, dto);
            return StatusCode(201, result);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}/submit
        // Soumettre un brouillon — uniquement le créateur de la demande
        // -------------------------------------------------------
        [HttpPut("{id}/submit")]
        public async Task<IActionResult> Submit(int id)
        {
            var userId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            if (userId == null)
                return Unauthorized(new { message = "Utilisateur non identifié." });

            // La vérification que l'utilisateur est bien le créateur
            // est faite dans le service (SubmitAsync)
            var result = await _requestService.SubmitAsync(id, userId);
            return Ok(result);
        }

        // -------------------------------------------------------
        // GET /api/requests
        // Client voit ses demandes, les autres voient tout
        // -------------------------------------------------------
        [HttpGet]
        public async Task<IActionResult> GetAll([FromQuery] string? status = null)
        {
            var userId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            if (User.IsInRole("Client"))
            {
                var clientRequests = await _requestService.GetByClientAsync(userId!);
                return Ok(clientRequests);
            }

            var requests = await _requestService.GetAllAsync(status);
            return Ok(requests);
        }

        // -------------------------------------------------------
        // GET /api/requests/{id}
        // Détail d'une demande — tous les rôles connectés
        // -------------------------------------------------------
        [HttpGet("{id}")]
        public async Task<IActionResult> GetById(int id)
        {
            var request = await _requestService.GetByIdAsync(id);
            if (request == null)
                return NotFound(new { message = "Demande introuvable." });

            return Ok(request);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}/receive
        // Réceptionner — uniquement Receptionist (pas Admin)
        // -------------------------------------------------------
        [HttpPut("{id}/receive")]
        [Authorize(Policy = "RequireReceptionistOnly")]
        public async Task<IActionResult> Receive(int id)
        {
            var result = await _requestService.ReceiveAsync(id);
            return Ok(result);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}/assign
        // Assigner — uniquement Receptionist, uniquement vers un Analyst
        // -------------------------------------------------------
        [HttpPut("{id}/assign")]
        [Authorize(Policy = "RequireReceptionistOnly")]
        public async Task<IActionResult> Assign(int id, [FromBody] string analystId)
        {
            // Vérifier que l'utilisateur cible existe
            var analyst = await _userManager.FindByIdAsync(analystId);
            if (analyst == null)
                return NotFound(new { message = "Utilisateur introuvable." });

            // Vérifier que l'utilisateur cible a bien le rôle Analyst
            var roles = await _userManager.GetRolesAsync(analyst);
            if (!roles.Contains("Analyst"))
                return BadRequest(new { message = "L'utilisateur sélectionné n'est pas un laborantin." });

            var result = await _requestService.AssignAsync(id, analystId);
            return Ok(result);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}/reject
        // Refuser — uniquement Receptionist
        // -------------------------------------------------------
        [HttpPut("{id}/reject")]
        [Authorize(Policy = "RequireReceptionistOnly")]
        public async Task<IActionResult> Reject(int id, [FromBody] string reason)
        {
            var result = await _requestService.RejectAsync(id, reason);
            return Ok(result);
        }

        // -------------------------------------------------------
        // POST /api/requests/{id}/results
        // Saisir les résultats — uniquement Analyst (pas Admin)
        // -------------------------------------------------------
        [HttpPost("{id}/results")]
        [Authorize(Policy = "RequireAnalystOnly")]
        public async Task<IActionResult> SaveResults(int id, [FromBody] List<SaveResultDto> results)
        {
            var analystId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            if (analystId == null)
                return Unauthorized(new { message = "Utilisateur non identifié." });

            var result = await _requestService.SaveResultsAsync(id, analystId, results);
            return Ok(result);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}/complete-analysis
        // Terminer l'analyse — uniquement Analyst (pas Admin)
        // -------------------------------------------------------
        [HttpPut("{id}/complete-analysis")]
        [Authorize(Policy = "RequireAnalystOnly")]
        public async Task<IActionResult> CompleteAnalysis(int id)
        {
            var analystId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            if (analystId == null)
                return Unauthorized(new { message = "Utilisateur non identifié." });

            var result = await _requestService.CompleteAnalysisAsync(id, analystId);
            return Ok(result);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}/validate
        // Valider — uniquement LabChief (pas Admin)
        // -------------------------------------------------------
        [HttpPut("{id}/validate")]
        [Authorize(Policy = "RequireLabChiefOnly")]
        public async Task<IActionResult> Validate(int id)
        {
            var labChiefId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            if (labChiefId == null)
                return Unauthorized(new { message = "Utilisateur non identifié." });

            var result = await _requestService.ValidateAsync(id, labChiefId);
            return Ok(result);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}/invalidate
        // Rejeter — uniquement LabChief (pas Admin)
        // -------------------------------------------------------
        [HttpPut("{id}/invalidate")]
        [Authorize(Policy = "RequireLabChiefOnly")]
        public async Task<IActionResult> Invalidate(int id, [FromBody] string reason)
        {
            var labChiefId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            if (labChiefId == null)
                return Unauthorized(new { message = "Utilisateur non identifié." });

            var result = await _requestService.InvalidateAsync(id, labChiefId, reason);
            return Ok(result);
        }

        // -------------------------------------------------------
        // GET /api/requests/{id}/history
        // Historique — uniquement Admin et LabChief
        // -------------------------------------------------------
        [HttpGet("{id}/history")]
        [Authorize(Policy = "RequireAdminOrLabChief")]
        public async Task<IActionResult> GetHistory(int id)
        {
            var history = await _requestService.GetHistoryAsync(id);
            return Ok(history);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}/deadlines
        // Définir les échéances — Receptionist et Admin uniquement
        // -------------------------------------------------------
        [HttpPut("{id}/deadlines")]
        [Authorize(Policy = "RequireClientRole")]
        public async Task<IActionResult> SetDeadlines(
            int id,
            [FromBody] List<SetDeadlineDto> deadlines)
        {
            // Récupérer l'ID de l'utilisateur connecté
            var userId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
            ?? User.FindFirst("sub")?.Value;
            
            // Vérifier que la demande existe
            var request = await _requestService.GetByIdAsync(id);
            if (request == null)
                return NotFound(new { message = "Demande introuvable." });

            // Vérifier que c'est bien le créateur de la demande qui définit les échéances ou l'admin 
            if (request.ClientId != userId && !User.IsInRole("Administrator"))
                return StatusCode(403, new { message = "Seul le créateur de la demande ou un administrateur peut définir les échéances." });
            
            var result = await _requestService.SetDeadlinesAsync(id, deadlines);
            return Ok(result);
        }

        // -------------------------------------------------------
        // GET /api/requests/{id}/deadlines
        // Consulter les échéances — tous les rôles connectés
        // -------------------------------------------------------
        [HttpGet("{id}/deadlines")]
        public async Task<IActionResult> GetDeadlines(int id)
        {
            var deadlines = await _requestService.GetDeadlinesAsync(id);
            return Ok(deadlines);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}
        // Modifier une demande — uniquement le créateur ou l'Admin
        // Uniquement si la demande est en brouillon
        // -------------------------------------------------------
        [HttpPut("{id}")]
        [Authorize(Policy = "RequireClientRole")]
        public async Task<IActionResult> Update(int id, [FromBody] UpdateRequestDto dto)
        {
            var userId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            if (userId == null)
                return Unauthorized(new { message = "Utilisateur non identifié." });

            // Vérifier que la demande existe
            var request = await _requestService.GetByIdAsync(id);
            if (request == null)
                return NotFound(new { message = "Demande introuvable." });

            // Vérifier le statut
            if (request.Status != "Draft")
                return BadRequest(new { message = "Seules les demandes en brouillon peuvent être modifiées." });

            // Vérifier que c'est le créateur ou un Admin
            if (request.ClientId != userId && !User.IsInRole("Administrator"))
                return StatusCode(403, new { message = "Seul le créateur de la demande peut la modifier." });

            var result = await _requestService.UpdateAsync(id, userId, dto);
            return Ok(result);
        }
    }

}