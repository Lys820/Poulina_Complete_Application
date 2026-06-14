using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace PouleLabApp.API.Migrations
{
    /// <inheritdoc />
    public partial class AddTemplateTypeToLaboratory : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "TemplateType",
                table: "Laboratories",
                type: "int",
                nullable: false,
                defaultValue: 0);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "TemplateType",
                table: "Laboratories");
        }
    }
}
