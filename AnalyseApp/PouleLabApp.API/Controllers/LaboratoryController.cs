using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using PouleLabApp.API.Data;
using PouleLabApp.API.Models;

namespace PouleLabApp.API.Controllers
{
    [ApiController]
    [Route("api/laboratories")]
    [Authorize]
    public class LaboratoryController : ControllerBase
    {
        private readonly ApplicationDbContext _context;

        public LaboratoryController(ApplicationDbContext context)
        {
            _context = context;
        }

<<<<<<< HEAD
        // -------------------------------------------------------
        // GET /api/laboratories
        // -------------------------------------------------------
=======
        // GET /api/laboratories
>>>>>>> origin/Lilia
        [HttpGet]
        [AllowAnonymous]
        public async Task<IActionResult> GetAll()
        {
            var labs = await _context.Laboratories
<<<<<<< HEAD
                .Select(l => new {
                    l.Id,
                    l.Name,
                    l.Description,
                    l.Address,
                    MemberCount = _context.Users
                        .Count(u => u.LaboratoryId == l.Id)
                })
=======
                .Select(l => new { l.Id, l.Name, l.Description, l.Address })
>>>>>>> origin/Lilia
                .ToListAsync();
            return Ok(labs);
        }

<<<<<<< HEAD
        // -------------------------------------------------------
        // GET /api/laboratories/{id}
        // -------------------------------------------------------
        [HttpGet("{id}")]
        public async Task<IActionResult> GetById(int id)
        {
            var lab = await _context.Laboratories
                .Where(l => l.Id == id)
                .Select(l => new {
                    l.Id,
                    l.Name,
                    l.Description,
                    l.Address,
                    MemberCount = _context.Users
                        .Count(u => u.LaboratoryId == l.Id)
                })
                .FirstOrDefaultAsync();

            if (lab == null)
                return NotFound(new { message = "Laboratoire introuvable." });

            return Ok(lab);
        }

        // -------------------------------------------------------
        // POST /api/laboratories — Admin crée un labo
        // -------------------------------------------------------
=======
        // GET /api/laboratories/{id}
        [HttpGet("{id}")]
        public async Task<IActionResult> GetById(int id)
        {
            var lab = await _context.Laboratories.FindAsync(id);
            if (lab == null)
                return NotFound(new { message = "Laboratoire introuvable." });
            return Ok(new { lab.Id, lab.Name, lab.Description, lab.Address });
        }

        // POST /api/laboratories
>>>>>>> origin/Lilia
        [HttpPost]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> Create([FromBody] LaboratoryDto dto)
        {
<<<<<<< HEAD
            if (string.IsNullOrWhiteSpace(dto.Name))
                return BadRequest(new { message = "Le nom est obligatoire." });

            var existing = await _context.Laboratories
                .AnyAsync(l => l.Name.ToLower() == dto.Name.ToLower().Trim());
            if (existing)
=======
            if (string.IsNullOrEmpty(dto.Name))
                return BadRequest(new { message = "Le nom est obligatoire." });

            var exists = await _context.Laboratories
                .AnyAsync(l => l.Name.ToLower() == dto.Name.ToLower());
            if (exists)
>>>>>>> origin/Lilia
                return BadRequest(new {
                    message = "Un laboratoire avec ce nom existe déjà."
                });

            var lab = new Laboratory
            {
<<<<<<< HEAD
                Name        = dto.Name.Trim(),
                Description = dto.Description?.Trim() ?? string.Empty,
                Address     = dto.Address?.Trim() ?? string.Empty
=======
                Name        = dto.Name,
                Description = dto.Description ?? string.Empty,
                Address     = dto.Address ?? string.Empty
>>>>>>> origin/Lilia
            };

            _context.Laboratories.Add(lab);
            await _context.SaveChangesAsync();

<<<<<<< HEAD
            return Ok(new { message = $"Laboratoire '{lab.Name}' créé.", lab.Id });
        }

        // -------------------------------------------------------
        // PUT /api/laboratories/{id} — Admin modifie un labo
        // -------------------------------------------------------
=======
            return StatusCode(201, new {
                lab.Id, lab.Name, lab.Description, lab.Address,
                message = "Laboratoire créé avec succès."
            });
        }

        // PUT /api/laboratories/{id}
>>>>>>> origin/Lilia
        [HttpPut("{id}")]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> Update(int id, [FromBody] LaboratoryDto dto)
        {
            var lab = await _context.Laboratories.FindAsync(id);
            if (lab == null)
                return NotFound(new { message = "Laboratoire introuvable." });

<<<<<<< HEAD
            if (string.IsNullOrWhiteSpace(dto.Name))
                return BadRequest(new { message = "Le nom est obligatoire." });

            // Vérifier doublon de nom (sauf pour lui-même)
            var duplicate = await _context.Laboratories
                .AnyAsync(l => l.Name.ToLower() == dto.Name.ToLower().Trim()
                            && l.Id != id);
            if (duplicate)
                return BadRequest(new {
                    message = "Un autre laboratoire porte déjà ce nom."
                });

            lab.Name        = dto.Name.Trim();
            lab.Description = dto.Description?.Trim() ?? string.Empty;
            lab.Address     = dto.Address?.Trim() ?? string.Empty;

            await _context.SaveChangesAsync();

            return Ok(new { message = $"Laboratoire '{lab.Name}' mis à jour." });
        }

        // -------------------------------------------------------
        // DELETE /api/laboratories/{id} — Admin supprime un labo
        // -------------------------------------------------------
=======
            // Vérifier doublon de nom (exclure le labo actuel)
            var exists = await _context.Laboratories
                .AnyAsync(l => l.Name.ToLower() == dto.Name.ToLower() && l.Id != id);
            if (exists)
                return BadRequest(new {
                    message = "Un laboratoire avec ce nom existe déjà."
                });

            lab.Name        = dto.Name;
            lab.Description = dto.Description ?? string.Empty;
            lab.Address     = dto.Address ?? string.Empty;

            await _context.SaveChangesAsync();

            return Ok(new { message = "Laboratoire mis à jour avec succès." });
        }

        // DELETE /api/laboratories/{id}
>>>>>>> origin/Lilia
        [HttpDelete("{id}")]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> Delete(int id)
        {
            var lab = await _context.Laboratories.FindAsync(id);
            if (lab == null)
                return NotFound(new { message = "Laboratoire introuvable." });

<<<<<<< HEAD
            // Vérifier qu'aucun utilisateur n'est encore rattaché
=======
            // Vérifier s'il y a des utilisateurs liés
>>>>>>> origin/Lilia
            var hasUsers = await _context.Users
                .AnyAsync(u => u.LaboratoryId == id);
            if (hasUsers)
                return BadRequest(new {
<<<<<<< HEAD
                    message = "Impossible de supprimer : des utilisateurs sont rattachés à ce laboratoire."
                });

            // Vérifier qu'aucune demande active n'est liée à ce labo
            var hasActiveRequests = await _context.AnalysisRequests
                .AnyAsync(r => r.LaboratoryId == id &&
                          r.Status != RequestStatus.Validated &&
                          r.Status != RequestStatus.Closed);
            if (hasActiveRequests)
                return BadRequest(new {
                    message = "Impossible de supprimer : des demandes actives sont liées à ce laboratoire."
=======
                    message = "Impossible de supprimer : des utilisateurs " +
                              "sont rattachés à ce laboratoire."
                });

            // Vérifier s'il y a des demandes liées
            var hasRequests = await _context.AnalysisRequests
                .AnyAsync(r => r.LaboratoryId == id);
            if (hasRequests)
                return BadRequest(new {
                    message = "Impossible de supprimer : des demandes " +
                              "sont liées à ce laboratoire."
>>>>>>> origin/Lilia
                });

            _context.Laboratories.Remove(lab);
            await _context.SaveChangesAsync();

<<<<<<< HEAD
            return Ok(new { message = $"Laboratoire '{lab.Name}' supprimé." });
=======
            return Ok(new { message = "Laboratoire supprimé avec succès." });
>>>>>>> origin/Lilia
        }
    }

    // DTO
    public class LaboratoryDto
    {
        public string  Name        { get; set; } = string.Empty;
        public string? Description { get; set; }
        public string? Address     { get; set; }
    }
}