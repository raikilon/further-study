import { Pipe, PipeTransform } from '@angular/core';
import { Program } from '../program.model';

@Pipe({ name: 'programFee', standalone: true, pure: true })
export class ProgramFeePipe implements PipeTransform {
  transform(program: Program): string {
    if (program.priceCHF === null) return 'Not listed';
    const amount = new Intl.NumberFormat('en-CH', { maximumFractionDigits: 0 }).format(program.priceCHF);
    const prefix = program.priceNote === 'From' ? 'From ' : '';
    const suffix = program.priceNote && program.priceNote !== 'From' ? ` · ${program.priceNote}` : '';
    return `${prefix}CHF ${amount}${suffix}`;
  }
}
