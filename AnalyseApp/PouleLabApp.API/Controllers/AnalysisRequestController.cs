using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using PouleLabApp.API.DTOs.Request;
using PouleLabApp.API.Services.Interfaces;

namespace PouleLabApp.API.Controllers
{
    [ApiController]
    [Route("api/requests")]
    [Authorize] // JWT obligatoire pour tous les endpoints
    public class AnalysisRequestController : ControllerBase
    {
        private readonly IAnalysisRequestService _requestService;

        public AnalysisRequestController(IAnalysisRequestService requestService)
        {
            _requestService = requestService;
        }

        // -------------------------------------------------------
        // POST /api/requests
        // Créer une nouvelle demande (brouillon ou soumise)
        // Accessible à tous les utilisateurs connectés
        // -------------------------------------------------------
        [HttpPost]
        public async Task<IActionResult> Create([FromBody] CreateRequestDto dto)
        {
            // Récupérer l'ID du client connecté depuis le JWT
            var clientId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            if (clientId == null)
                return Unauthorized(new { message = "Utilisateur non identifié." });

            var result = await _requestService.CreateAsync(clientId, dto);
            return StatusCode(201, result);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}/submit
        // Soumettre un brouillon existant
        // -------------------------------------------------------
        [HttpPut("{id}/submit")]
        public async Task<IActionResult> Submit(int id)
        {
            var clientId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            if (clientId == null)
                return Unauthorized(new { message = "Utilisateur non identifié." });

            var result = await _requestService.SubmitAsync(id, clientId);
            return Ok(result);
        }

        // -------------------------------------------------------
        // GET /api/requests
        // Liste toutes les demandes (Admin/Manager/Receptionist)
        // ou seulement les siennes (Client)
        // -------------------------------------------------------
        [HttpGet]
        public async Task<IActionResult> GetAll([FromQuery] string? status = null)
        {
            var clientId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            // Un Client ne voit que ses propres demandes
            if (User.IsInRole("Client"))
            {
                var clientRequests = await _requestService.GetByClientAsync(clientId!);
                return Ok(clientRequests);
            }

            // Les autres rôles voient toutes les demandes (avec filtre optionnel)
            var requests = await _requestService.GetAllAsync(status);
            return Ok(requests);
        }

        // -------------------------------------------------------
        // GET /api/requests/{id}
        // Récupérer le détail d'une demande
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
        // Réceptionner une demande (Réceptionniste)
        // -------------------------------------------------------
        [HttpPut("{id}/receive")]
        [Authorize(Policy = "RequireReceptionist")]
        public async Task<IActionResult> Receive(int id)
        {
            var result = await _requestService.ReceiveAsync(id);
            return Ok(result);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}/assign
        // Assigner une demande à un laborantin (Réceptionniste)
        // -------------------------------------------------------
        [HttpPut("{id}/assign")]
        [Authorize(Policy = "RequireReceptionist")]
        public async Task<IActionResult> Assign(int id, [FromBody] string analystId)
        {
            var result = await _requestService.AssignAsync(id, analystId);
            return Ok(result);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}/reject
        // Refuser une demande
        // -------------------------------------------------------
        [HttpPut("{id}/reject")]
        [Authorize(Policy = "RequireReceptionist")]
        public async Task<IActionResult> Reject(int id, [FromBody] string reason)
        {
            var result = await _requestService.RejectAsync(id, reason);
            return Ok(result);
        }

        // -------------------------------------------------------
        // POST /api/requests/{id}/results
        // Saisir les résultats d'analyse (Laborantin)
        // -------------------------------------------------------
        [HttpPost("{id}/results")]
        [Authorize(Policy = "RequireAnalyst")]
        public async Task<IActionResult> SaveResults(int id, [FromBody] List<SaveResultDto> results)
        {
            // Récupérer l'ID du laborantin connecté depuis le JWT
            var analystId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            if (analystId == null)
                return Unauthorized(new { message = "Utilisateur non identifié." });

            var result = await _requestService.SaveResultsAsync(id, analystId, results);
            return Ok(result);
        }

        // -------------------------------------------------------
        // PUT /api/requests/{id}/complete-analysis
        // Marquer les analyses comme terminées (Laborantin)
        // -------------------------------------------------------
        [HttpPut("{id}/complete-analysis")]
        [Authorize(Policy = "RequireAnalyst")]
        public async Task<IActionResult> CompleteAnalysis(int id)
        {
            var analystId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value
                ?? User.FindFirst("sub")?.Value;

            if (analystId == null)
                return Unauthorized(new { message = "Utilisateur non identifié." });

            var result = await _requestService.CompleteAnalysisAsync(id, analystId);
            return Ok(result);
        }
    }
}