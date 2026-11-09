import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'programDate', standalone: true, pure: true })
export class ProgramDatePipe implements PipeTransform {
  transform(date: string | null, label?: string | null): string {
    if (!date) return label || 'To be announced';
    return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' })
      .format(new Date(`${date}T00:00:00`));
  }
}
