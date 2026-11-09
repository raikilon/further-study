import { Pipe, PipeTransform } from '@angular/core';
import { ProgramFormat } from '../program.model';
import { FORMAT_LABELS } from '../catalog/catalog-labels';

@Pipe({ name: 'formatLabel', standalone: true, pure: true })
export class FormatLabelPipe implements PipeTransform {
  transform(format: ProgramFormat): string {
    return format ? FORMAT_LABELS[format] ?? format : 'Not specified';
  }
}
