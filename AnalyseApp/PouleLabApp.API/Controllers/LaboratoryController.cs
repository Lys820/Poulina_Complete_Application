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
        public LaboratoryController(ApplicationDbContext context) { _context = context; }

        [HttpGet]
        [AllowAnonymous]
        public async Task<IActionResult> GetAll()
        {
            var labs = await _context.Laboratories
                .Select(l => new { l.Id, l.Name, l.Description, l.Address })
                .ToListAsync();
            return Ok(labs);
        }

        [HttpGet("{id}")]
        public async Task<IActionResult> GetById(int id)
        {
            var lab = await _context.Laboratories.FindAsync(id);
            if (lab == null) return NotFound(new { message = "Laboratoire introuvable." });
            return Ok(new { lab.Id, lab.Name, lab.Description, lab.Address });
        }

        [HttpPost]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> Create([FromBody] LaboratoryDto dto)
        {
            if (string.IsNullOrEmpty(dto.Name))
                return BadRequest(new { message = "Le nom est obligatoire." });

            var exists = await _context.Laboratories
                .AnyAsync(l => l.Name.ToLower() == dto.Name.ToLower());
            if (exists)
                return BadRequest(new { message = "Un laboratoire avec ce nom existe déjà." });

            var lab = new Laboratory
            {
                Name        = dto.Name,
                Description = dto.Description ?? string.Empty,
                Address     = dto.Address ?? string.Empty
            };
            _context.Laboratories.Add(lab);
            await _context.SaveChangesAsync();

            return StatusCode(201, new {
                lab.Id, lab.Name, lab.Description, lab.Address,
                message = "Laboratoire créé avec succès."
            });
        }

        [HttpPut("{id}")]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> Update(int id, [FromBody] LaboratoryDto dto)
        {
            var lab = await _context.Laboratories.FindAsync(id);
            if (lab == null) return NotFound(new { message = "Laboratoire introuvable." });

            var exists = await _context.Laboratories
                .AnyAsync(l => l.Name.ToLower() == dto.Name.ToLower() && l.Id != id);
            if (exists)
                return BadRequest(new { message = "Un laboratoire avec ce nom existe déjà." });

            lab.Name        = dto.Name;
            lab.Description = dto.Description ?? string.Empty;
            lab.Address     = dto.Address ?? string.Empty;
            await _context.SaveChangesAsync();

            return Ok(new { message = "Laboratoire mis à jour avec succès." });
        }

        [HttpDelete("{id}")]
        [Authorize(Policy = "RequireAdmin")]
        public async Task<IActionResult> Delete(int id)
        {
            var lab = await _context.Laboratories.FindAsync(id);
            if (lab == null) return NotFound(new { message = "Laboratoire introuvable." });

            var hasUsers = await _context.Users.AnyAsync(u => u.LaboratoryId == id);
            if (hasUsers)
                return BadRequest(new {
                    message = "Impossible de supprimer : des utilisateurs sont rattachés à ce laboratoire."
                });

            var hasRequests = await _context.AnalysisRequests.AnyAsync(r => r.LaboratoryId == id);
            if (hasRequests)
                return BadRequest(new {
                    message = "Impossible de supprimer : des demandes sont liées à ce laboratoire."
                });

            _context.Laboratories.Remove(lab);
            await _context.SaveChangesAsync();
            return Ok(new { message = "Laboratoire supprimé avec succès." });
        }
    }

    public class LaboratoryDto
    {
        public string  Name        { get; set; } = string.Empty;
        public string? Description { get; set; }
        public string? Address     { get; set; }
    }
}
