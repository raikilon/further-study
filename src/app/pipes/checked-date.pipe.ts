import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'checkedDate', standalone: true, pure: true })
export class CheckedDatePipe implements PipeTransform {
  transform(date: string): string {
    return new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short', year: 'numeric' })
      .format(new Date(`${date}T00:00:00`));
  }
}
